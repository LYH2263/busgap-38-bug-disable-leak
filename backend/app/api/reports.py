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

INACTIVE_DETAIL = "线路已停用"
NO_ARRIVALS_DETAIL = "没有到站"


def _get_line_or_404(db: Session, line_id: int) -> Line:
    line = db.get(Line, line_id)
    if not line:
        raise HTTPException(404, "线路不存在")
    return line


def _detect_events(line: Line, db: Session, stop_name: str | None) -> list[dict]:
    """计算间隔事件，不落库。停用语义和空到站语义互斥。"""
    trips = db.scalars(select(Trip).where(Trip.line_id == line.id)).all()
    if not trips:
        raise HTTPException(404, NO_ARRIVALS_DETAIL)
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids))).all()
    payload = [{"stop_name": a.stop_name, "trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive}
               for a in arrivals if stop_name is None or a.stop_name == stop_name]
    events = detect_bunching(payload, line.planned_headway_min, line.bunch_threshold, line.large_threshold)
    data = events_to_dicts(events)
    return [{**e, 'status': stamp_status(e.get('status', 'normal'))} for e in data]


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    # 历史报告只读：线路停用后旧报告仍须可见，且不被参与集裁剪改写。
    rows = db.scalars(select(BunchReport).order_by(BunchReport.id.desc())).all()
    return [{"id": r.id, "line_id": r.line_id, "stop_name": r.stop_name,
             "created_at": r.created_at.isoformat(), "events": json.loads(r.summary_json)} for r in rows]


@router.post("/run")
def run_detection(line_id: int, stop_name: str | None = None, db: Session = Depends(get_db)):
    line = _get_line_or_404(db, line_id)
    if not line.is_active:
        raise HTTPException(409, INACTIVE_DETAIL)
    data = _detect_events(line, db, stop_name)
    report = BunchReport(line_id=line_id, stop_name=stop_name or "*", created_at=datetime.utcnow(),
                         summary_json=json.dumps(data, ensure_ascii=False))
    db.add(report); db.commit(); db.refresh(report)
    return {"id": report.id, "events": data}


@router.get("/suggestions")
def suggestions(line_id: int, db: Session = Depends(get_db)):
    line = _get_line_or_404(db, line_id)
    if not line.is_active:
        raise HTTPException(409, INACTIVE_DETAIL)
    # 试算只返回建议，不落库，不与已存报告共用写入路径。
    data = _detect_events(line, db, None)
    return {"line_id": line_id, "suggestions": [e for e in data if e["status"] != "normal"]}


@router.get("/timeline")
def timeline(line_id: int, stop_name: str = "市民中心", db: Session = Depends(get_db)):
    line = _get_line_or_404(db, line_id)
    is_active = bool(line.is_active)
    # 轴可打开停用线：返回 200 + is_active=false，只给历史到站，不报错、不发起检测、不产生报告。
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    arrivals = sorted(db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids), Arrival.stop_name == stop_name)).all(),
                      key=lambda a: a.actual_arrive)
    if not arrivals:
        return {"stop_name": stop_name, "marks": [], "is_active": is_active}
    t0 = arrivals[0].actual_arrive
    span = max((arrivals[-1].actual_arrive - t0).total_seconds(), 1)
    marks = [{"trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive.isoformat(),
              "pct": round((a.actual_arrive - t0).total_seconds() / span * 100, 2)} for a in arrivals]
    return {"stop_name": stop_name, "marks": flatten_marks(marks), "is_active": is_active}
