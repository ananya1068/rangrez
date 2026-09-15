from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import generate_otp, create_access_token, get_current_user
from app.config import settings
from app.database import get_db
from app.models import OTP, User
from app.schemas import RequestOTPIn, RequestOTPOut, VerifyOTPIn, TokenOut, UserOut, UserUpdateIn

router = APIRouter(prefix="/api/auth", tags=["auth"])

OTP_VALIDITY_SECONDS = 300


@router.post("/request-otp", response_model=RequestOTPOut)
def request_otp(payload: RequestOTPIn, db: Session = Depends(get_db)):
    code = generate_otp()
    otp = OTP(phone=payload.phone, code=code)
    db.add(otp)
    db.commit()

    return RequestOTPOut(
        phone=payload.phone,
        otp_sent=True,
        # Demo mode only: real deployments would send this via an SMS gateway and
        # omit it from the API response entirely.
        demo_otp=code if settings.MOCK_SMS_MODE else None,
        expires_in_seconds=OTP_VALIDITY_SECONDS,
    )


@router.post("/verify-otp", response_model=TokenOut)
def verify_otp(payload: VerifyOTPIn, db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(seconds=OTP_VALIDITY_SECONDS)
    otp_row = (
        db.query(OTP)
        .filter(OTP.phone == payload.phone, OTP.code == payload.otp, OTP.consumed == False)  # noqa: E712
        .filter(OTP.created_at >= cutoff)
        .order_by(OTP.created_at.desc())
        .first()
    )
    if not otp_row:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP. Please request a new one.")

    otp_row.consumed = True

    user = db.query(User).filter(User.phone == payload.phone).first()
    if not user:
        user = User(
            phone=payload.phone,
            role=payload.role,
            name=payload.name or "",
            region=payload.region or "Kutch, Gujarat",
        )
        db.add(user)
    else:
        user.role = payload.role
        if payload.name:
            user.name = payload.name
        if payload.region:
            user.region = payload.region

    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
