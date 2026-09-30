import os
import tempfile

_db_path = os.path.join(tempfile.gettempdir(), "busgap_test_line_status.db")
if os.path.exists(_db_path):
    os.remove(_db_path)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.models import Line


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# 停用前生成的报告快照，用于验证停用/启用都不改写历史报告内容。
_snapshot: dict = {}


def test_seed_line_active_by_default(client):
    rows = client.get("/api/lines").json()
    assert rows, "种子数据应已生成"
    line = next(r for r in rows if r["code"] == "B12")
    assert line["is_active"] is True


def test_detection_works_while_active(client):
    res = client.post("/api/reports/run?line_id=1")
    assert res.status_code == 200
    body = res.json()
    assert "events" in body
    _snapshot["report_id"] = body["id"]
    _snapshot["events"] = body["events"]
    assert body["events"], "种子数据应能跑出间隔事件"


def test_deactivate_blocks_run_and_suggestions(client):
    res = client.post("/api/lines/1/deactivate")
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    run = client.post("/api/reports/run?line_id=1")
    assert run.status_code == 409
    assert run.json()["detail"] == "线路已停用"

    sug = client.get("/api/reports/suggestions?line_id=1")
    assert sug.status_code == 409
    assert sug.json()["detail"] == "线路已停用"


def test_deactivated_state_persists_on_relist(client):
    rows = client.get("/api/lines").json()
    assert next(r for r in rows if r["id"] == 1)["is_active"] is False


def test_blocked_detection_and_trial_create_no_report(client):
    before = len(client.get("/api/reports").json())
    for _ in range(3):
        assert client.post("/api/reports/run?line_id=1").status_code == 409
        assert client.get("/api/reports/suggestions?line_id=1").status_code == 409
    after = client.get("/api/reports").json()
    assert len(after) == before, "检测/试算被拦时不得写入任何新报告"


def test_timeline_still_works_when_deactivated(client):
    res = client.get("/api/reports/timeline?line_id=1")
    assert res.status_code == 200
    body = res.json()
    assert body["is_active"] is False
    assert body["marks"], "停用期间时间轴仍返回历史到站记录"


def test_opening_timeline_creates_no_report(client):
    before = client.get("/api/reports").json()
    assert {r["id"] for r in before}  # 存在停用前的历史报告
    for _ in range(2):
        assert client.get("/api/reports/timeline?line_id=1").status_code == 200
    after = client.get("/api/reports").json()
    assert [r["id"] for r in after] == [r["id"] for r in before], "打开轴不得多一条报告"


def test_history_reports_visible_when_deactivated(client):
    res = client.get("/api/reports")
    assert res.status_code == 200
    assert any(r["line_id"] == 1 for r in res.json()), "停用前生成的历史报告仍可查看"


def test_deactivation_does_not_rewrite_history(client):
    rows = client.get("/api/reports").json()
    snap = next(r for r in rows if r["id"] == _snapshot["report_id"])
    assert snap["events"] == _snapshot["events"], "停用不得改写已存报告内容"


def test_active_empty_line_says_no_arrivals_not_inactive(client):
    db = SessionLocal()
    try:
        line = Line(code="EMPTY", name="空载试算线", planned_headway_min=8.0,
                    bunch_threshold=3.0, large_threshold=15.0, is_active=True)
        db.add(line)
        db.commit()
        db.refresh(line)
        empty_id = line.id
    finally:
        db.close()

    # 运营中但无到站：只能说没有到站，不能装成停用。
    run = client.post(f"/api/reports/run?line_id={empty_id}")
    assert run.status_code == 404
    assert run.json()["detail"] == "没有到站"

    client.post(f"/api/lines/{empty_id}/deactivate")

    # 停用后：停用判定优先，只能说线路已停用，与「没有到站」互斥。
    run2 = client.post(f"/api/reports/run?line_id={empty_id}")
    assert run2.status_code == 409
    assert run2.json()["detail"] == "线路已停用"
    sug = client.get(f"/api/reports/suggestions?line_id={empty_id}")
    assert sug.status_code == 409
    assert sug.json()["detail"] == "线路已停用"
    # 停用空线仍可打开轴（只读、不报错），只是没有历史点。
    tl = client.get(f"/api/reports/timeline?line_id={empty_id}")
    assert tl.status_code == 200
    assert tl.json()["is_active"] is False
    assert tl.json()["marks"] == []


def test_activate_resumes_detection_and_trial_together(client):
    res = client.post("/api/lines/1/activate")
    assert res.status_code == 200
    assert res.json()["is_active"] is True

    # 检测与试算必须一起恢复，禁止只恢复其中一处。
    run = client.post("/api/reports/run?line_id=1")
    assert run.status_code == 200
    assert "events" in run.json()

    sug = client.get("/api/reports/suggestions?line_id=1")
    assert sug.status_code == 200
    assert "suggestions" in sug.json()

    tl = client.get("/api/reports/timeline?line_id=1")
    assert tl.status_code == 200
    assert tl.json()["is_active"] is True

    # 恢复后旧报告内容仍保持原样。
    rows = client.get("/api/reports").json()
    snap = next(r for r in rows if r["id"] == _snapshot["report_id"])
    assert snap["events"] == _snapshot["events"], "重新启用也不得改写历史报告"


def test_unknown_line_returns_404(client):
    assert client.post("/api/lines/9999/deactivate").status_code == 404
    assert client.post("/api/reports/run?line_id=9999").status_code == 404
    assert client.get("/api/reports/suggestions?line_id=9999").status_code == 404
    assert client.get("/api/reports/timeline?line_id=9999").status_code == 404
