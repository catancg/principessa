import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.db.session import get_db
from app.schemas.signup import SignupRequest, validate_mx
from app.services.signup_service import create_signup

logger = logging.getLogger(__name__)

router = APIRouter(tags=["signup"])


@router.post("/signup")
@limiter.limit("10/minute")
def signup(request: Request, payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        validate_mx(payload.email)
        customer_id, identity_id, is_new = create_signup(db, payload)
        db.commit()
        if not is_new:
            raise HTTPException(status_code=409, detail="already_registered")
        return {"ok": True, "customer_id": str(customer_id), "identity_id": str(identity_id)}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.error("Signup failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Signup failed, please try again")
