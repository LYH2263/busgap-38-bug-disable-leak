import os
import tempfile

_db_path = os.path.join(tempfile.gettempdir(), "busgap_test_line_status.db")
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


def test_seed_line_active_by_default(client):
    rows = client.get("/api/lines").json()
    assert rows, "种子数据应已生成"
    line = next(r for r in rows if r["code"] == "B12")
    assert line["is_active"] is True


def test_detection_works_while_active(client):
    res = client.post("/api/reports/run?line_id=1")
    assert res.status_code == 200
    assert "events" in res.json()


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


def test_timeline_still_works_when_deactivated(client):
    res = client.get("/api/reports/timeline?line_id=1")
    assert res.status_code == 200
    body = res.json()
    assert body["is_active"] is False
    assert body["marks"], "停用期间时间轴仍返回历史到站记录"


def test_history_reports_visible_when_deactivated(client):
    res = client.get("/api/reports")
    assert res.status_code == 200
    assert any(r["line_id"] == 1 for r in res.json()), "停用前生成的历史报告仍可查看"


def test_activate_resumes_detection(client):
    res = client.post("/api/lines/1/activate")
    assert res.status_code == 200
    assert res.json()["is_active"] is True

    run = client.post("/api/reports/run?line_id=1")
    assert run.status_code == 200
    assert "events" in run.json()


def test_unknown_line_returns_404(client):
    assert client.post("/api/lines/9999/deactivate").status_code == 404
    assert client.post("/api/reports/run?line_id=9999").status_code == 404
