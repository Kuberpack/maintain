from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_secret
from app.database import get_db
from app.models import User
from app.schemas.auth import PasswordLoginRequest, PinLoginRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login/pin", response_model=TokenResponse)
def login_with_pin(payload: PinLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.phone_number == payload.phone_number).first()
    if user is None or user.pin_hash is None or not verify_secret(payload.pin, user.pin_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid phone number or PIN")

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.post("/login/password", response_model=TokenResponse)
def login_with_password(payload: PasswordLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or user.password_hash is None or not verify_secret(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=UserPublic)
def get_me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(user)
