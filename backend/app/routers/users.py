import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.core.security import hash_secret
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import User, UserRole
from app.schemas.users import UserCreate, UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

# Full staff directory is supervisor+management; only supervisor writes
# (management is explicitly read-only per architecture.md). Operators see
# only themselves, via GET /auth/me.
_read_roles = require_roles(UserRole.supervisor, UserRole.management)
_write_roles = require_roles(UserRole.supervisor)


@router.get("", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _user=Depends(_read_roles)) -> list[User]:
    return db.query(User).order_by(User.name).all()


@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_read_roles)
) -> User:
    return get_or_404(db, User, user_id, "User not found")


@router.post("", response_model=UserPublic, status_code=201)
def create_user(
    payload: UserCreate, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> User:
    user = User(
        name=payload.name,
        role=payload.role,
        email=payload.email,
        phone_number=payload.phone_number,
        whatsapp_number=payload.whatsapp_number,
        pin_hash=hash_secret(payload.pin) if payload.pin else None,
        password_hash=hash_secret(payload.password) if payload.password else None,
    )
    db.add(user)
    commit_or_409(db, "A user with that email or phone number already exists")
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _user=Depends(_write_roles),
) -> User:
    user = get_or_404(db, User, user_id, "User not found")
    data = payload.model_dump(exclude_unset=True)

    pin = data.pop("pin", None)
    password = data.pop("password", None)
    for field, value in data.items():
        setattr(user, field, value)
    if pin is not None:
        user.pin_hash = hash_secret(pin)
    if password is not None:
        user.password_hash = hash_secret(password)

    # Exactly one credential per role. Clear whichever hash no longer applies
    # so a role change can't leave a stale login path open on the other
    # endpoint (e.g. an ex-operator promoted to management keeping a working
    # PIN login alongside their new password one).
    if user.role == UserRole.management:
        user.pin_hash = None
        if not user.password_hash:
            db.rollback()
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "management users require a password")
    else:
        user.password_hash = None
        if not user.pin_hash:
            db.rollback()
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "operator/supervisor users require a PIN")

    commit_or_409(db, "A user with that email or phone number already exists")
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> None:
    user = get_or_404(db, User, user_id, "User not found")
    db.delete(user)
    commit_or_409(db, "Cannot delete a user with existing task/repair/part history")
