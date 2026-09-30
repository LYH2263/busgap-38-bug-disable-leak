import os
import tempfile

_db_path = os.path.join(tempfile.gettempdir(), "busgap_test_gate.db")
if os.path.exists(_db_path):
    os.remove(_db_path)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _report_ids(client):
    return {r["id"]: r for r in client.get("/api/reports").json()}


def test_active_baseline_same_as_before(client):
    """未停用时跟底座相同：检测、试算、轴全部放行。"""
    run = client.post("/api/reports/run?line_id=1")
    assert run.status_code == 200
    assert run.json()["events"]

    sug = client.get("/api/reports/suggestions?line_id=1")
    assert sug.status_code == 200

    tl = client.get("/api/reports/timeline?line_id=1")
    assert tl.status_code == 200
    assert tl.json()["is_active"] is True
    assert tl.json()["marks"]


def test_suggestions_never_writes_reports(client):
    before = set(_report_ids(client))
    for _ in range(2):
        res = client.get("/api/reports/suggestions?line_id=1")
        assert res.status_code == 200
    after = set(_report_ids(client))
    assert before == after, "试算不得落库、不得多出报告"


def test_deactivate_gate_blocks_all_three(client):
    assert client.post("/api/lines/1/deactivate").json()["is_active"] is False

    run = client.post("/api/reports/run?line_id=1")
    assert run.status_code == 409
    assert run.json()["detail"] == "线路已停用"

    sug = client.get("/api/reports/suggestions?line_id=1")
    assert sug.status_code == 409
    assert sug.json()["detail"] == "线路已停用"

    tl = client.get("/api/reports/timeline?line_id=1")
    assert tl.status_code == 200
    assert tl.json()["is_active"] is False
    assert tl.json()["marks"], "停用期间轴仍展示历史到站"


def test_inactive_message_mutually_exclusive_with_no_arrivals(client):
    for res in (client.post("/api/reports/run?line_id=1"),
                client.get("/api/reports/suggestions?line_id=1")):
        assert res.status_code == 409
        detail = res.json()["detail"]
        assert detail == "线路已停用"
        assert detail != "没有到站", "停用失败不得写成没有到站"


def test_blocked_entries_create_no_new_reports(client):
    before = _report_ids(client)
    client.post("/api/reports/run?line_id=1")
    client.get("/api/reports/suggestions?line_id=1")
    # 多次打开轴也不得触发新检
    for _ in range(3):
        client.get("/api/reports/timeline?line_id=1")
    after = _report_ids(client)
    assert set(before) == set(after), "检测/试算/打开轴都不得新增报告"


def test_history_remains_and_is_not_rewritten(client):
    before = _report_ids(client)
    assert before, "停用前应已有历史报告"
    after = _report_ids(client)
    assert set(after) == set(before), "停用后历史报告整栏不得消失"
    for rid, report in before.items():
        kept = after[rid]
        assert kept["line_id"] == report["line_id"]
        assert kept["stop_name"] == report["stop_name"]
        assert kept["events"] == report["events"], "停用不得改写旧报告内容"


def test_activate_reopens_all_three_together(client):
    assert client.post("/api/lines/1/activate").json()["is_active"] is True

    run = client.post("/api/reports/run?line_id=1")
    assert run.status_code == 200 and run.json()["events"]

    sug = client.get("/api/reports/suggestions?line_id=1")
    assert sug.status_code == 200

    tl = client.get("/api/reports/timeline?line_id=1")
    assert tl.status_code == 200 and tl.json()["is_active"] is True


def test_unknown_line_timeline_is_404_not_no_arrivals_error(client):
    assert client.get("/api/reports/timeline?line_id=9999").status_code == 404
