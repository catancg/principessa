import os
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.jobs.weekly_scheduler import queue_weekly_promo

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin_key(x_admin_key: str | None = Header(default=None)):
    expected = os.getenv("ADMIN_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not set")
    if x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/queue-weekly", dependencies=[Depends(require_admin_key)])
def admin_queue_weekly(db: Session = Depends(get_db)):
    try:
        info = queue_weekly_promo(db)
        db.commit()
        return info
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"queue-weekly failed: {repr(e)}")
