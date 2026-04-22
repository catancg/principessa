from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.signup import SignupRequest, validate_mx
from app.services.signup_service import create_signup

router = APIRouter(tags=["signup"])

#@router.post("/signup")
#def signup(payload: SignupRequest, db: Session = Depends(get_db)):
#    customer_id, identity_id = create_signup(db, payload)
#    return {"ok": True, "customer_id": str(customer_id), "identity_id": str(identity_id)}
#
#from fastapi import HTTPException
#from sqlalchemy import text

@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    try:
        validate_mx(payload.email)
        customer_id, identity_id = create_signup(db, payload)
        db.commit()
        return {"ok": True, "customer_id": str(customer_id), "identity_id": str(identity_id)}
    except Exception as e:
        db.rollback()
        print("SIGNUP ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=f"signup failed: {repr(e)}")