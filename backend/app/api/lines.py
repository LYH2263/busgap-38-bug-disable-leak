from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Line
router = APIRouter(prefix="/lines", tags=["lines"])

def line_dict(r: Line) -> dict:
    return {"id": r.id, "code": r.code, "name": r.name, "planned_headway_min": r.planned_headway_min,
            "bunch_threshold": r.bunch_threshold, "large_threshold": r.large_threshold,
            "is_active": r.is_active}

@router.get("")
def list_lines(db: Session = Depends(get_db)):
    rows = db.scalars(select(Line).order_by(Line.id)).all()
    return [line_dict(r) for r in rows]

def _set_active(line_id: int, is_active: bool, db: Session) -> dict:
    line = db.get(Line, line_id)
    if not line:
        raise HTTPException(404, "线路不存在")
    line.is_active = is_active
    db.commit(); db.refresh(line)
    return line_dict(line)

@router.post("/{line_id}/deactivate")
def deactivate_line(line_id: int, db: Session = Depends(get_db)):
    return _set_active(line_id, False, db)

@router.post("/{line_id}/activate")
def activate_line(line_id: int, db: Session = Depends(get_db)):
    return _set_active(line_id, True, db)
