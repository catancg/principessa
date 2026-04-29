from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Optional, List
import dns.resolver
from fastapi import HTTPException

Channel = Literal["email", "instagram", "whatsapp", "sms"]
BabyStage = Literal["pregnant", "0_6m", "6_12m", "1_3y", "3y_plus"]

class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    interests: List[str] = Field(default_factory=list)
    consent_promotions: bool = True

class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    interests: List[str] = Field(default_factory=list)
    consent_promotions: bool = True

class SignupOut(BaseModel):
    customer_id: str
    identity_id: str

def validate_mx(email: str):
    domain = email.split("@")[1]
    try:
        dns.resolver.resolve(domain, "MX")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        raise HTTPException(status_code=400, detail="Email domain not valid")
    except Exception:
        pass  # fail open on transient DNS timeouts / network errors