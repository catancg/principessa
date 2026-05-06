import calendar
from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Literal, Optional, List
import dns.resolver
from fastapi import HTTPException

Channel = Literal["email", "instagram", "whatsapp", "sms"]
BabyStage = Literal["pregnant", "0_6m", "6_12m", "1_3y", "3y_plus"]

def _validate_birthday(birth_month, birth_day):
    if birth_month and birth_day:
        _, max_day = calendar.monthrange(2000, birth_month)  # 2000 = leap year, allows Feb 29
        if birth_day > max_day:
            raise ValueError(f"El día {birth_day} no es válido para el mes {birth_month}")

class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    interests: List[str] = Field(default_factory=list)
    consent_promotions: bool = True
    birth_month: Optional[int] = Field(default=None, ge=1, le=12)
    birth_day: Optional[int] = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def check_birthday(self):
        _validate_birthday(self.birth_month, self.birth_day)
        return self

class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    interests: List[str] = Field(default_factory=list)
    consent_promotions: bool = True
    birth_month: Optional[int] = Field(default=None, ge=1, le=12)
    birth_day: Optional[int] = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def check_birthday(self):
        _validate_birthday(self.birth_month, self.birth_day)
        return self

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