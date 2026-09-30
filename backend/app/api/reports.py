import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Arrival, BunchReport, Line, Trip
from app.services.bunch_engine import detect_bunching, events_to_dicts
from app.services.scope_helpers import flatten_marks, stamp_status
router = APIRouter(prefix="/reports", tags=["reports"])

LINE_INACTIVE_DETAIL = "线路已停用"
NO_ARRIVALS_DETAIL = "没有到站"


def require_active_line(line_id: int, db: Session) -> Line:
    """检测/试算/建议刷新的统一闸门：不存在 404，已停用 409（线路已停用）。

    停用判定先于「没有到站」，两种说明互斥，不允许互相串味。
    """
    line = db.get(Line, line_id)
    if not line:
        raise HTTPException(404, "线路不存在")
    if not line.is_active:
        raise HTTPException(409, LINE_INACTIVE_DETAIL)
    return line

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    # 历史报告只读长期保留：停用线路不藏报告、不参与任何过滤，
    # 停用/启用动作本身也绝不改写已存报告内容。
    rows = db.scalars(select(BunchReport).order_by(BunchReport.id.desc())).all()
    return [{"id": r.id, "line_id": r.line_id, "stop_name": r.stop_name,
             "created_at": r.created_at.isoformat(), "events": json.loads(r.summary_json)} for r in rows]

@router.post("/run")
def run_detection(line_id: int, stop_name: str | None = None, db: Session = Depends(get_db)):
    line = require_active_line(line_id, db)
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    if not trip_ids:
        raise HTTPException(404, NO_ARRIVALS_DETAIL)
    arrivals = db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids))).all()
    payload = [{"stop_name": a.stop_name, "trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive}
               for a in arrivals if stop_name is None or a.stop_name == stop_name]
    events = detect_bunching(payload, line.planned_headway_min, line.bunch_threshold, line.large_threshold)
    data = events_to_dicts(events)
    data = [{**e, 'status': stamp_status(e.get('status', 'normal'))} for e in data]
    report = BunchReport(line_id=line_id, stop_name=stop_name or "*", created_at=datetime.utcnow(),
                         summary_json=json.dumps(data, ensure_ascii=False))
    db.add(report); db.commit(); db.refresh(report)
    return {"id": report.id, "events": data}

@router.get("/suggestions")
def suggestions(line_id: int, db: Session = Depends(get_db)):
    # 走同一个 require_active_line 闸门：试算/建议刷新与检测同时被拦、同时恢复。
    result = run_detection(line_id=line_id, stop_name=None, db=db)
    return {"line_id": line_id, "suggestions": [e for e in result["events"] if e["status"] != "normal"]}

@router.get("/timeline")
def timeline(line_id: int, stop_name: str = "市民中心", db: Session = Depends(get_db)):
    # 轴是只读视图：停用后仍可打开，只带 is_active=False 提示，
    # 不报错、不跑检测，更不会因为打开轴而多一条报告。
    line = db.get(Line, line_id)
    if not line:
        raise HTTPException(404, "线路不存在")
    is_active = bool(line.is_active)
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = sorted(db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids), Arrival.stop_name == stop_name)).all(),
                      key=lambda a: a.actual_arrive)
    if not arrivals: return {"stop_name": stop_name, "marks": [], "is_active": is_active}
    t0 = arrivals[0].actual_arrive
    span = max((arrivals[-1].actual_arrive - t0).total_seconds(), 1)
    marks = [{"trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive.isoformat(),
              "pct": round((a.actual_arrive - t0).total_seconds() / span * 100, 2)} for a in arrivals]
    return {"stop_name": stop_name, "marks": flatten_marks(marks), "is_active": is_active}
