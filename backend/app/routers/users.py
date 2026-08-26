import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.security import hash_secret
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import User, UserAuditAction, UserAuditEvent, UserRole
from app.schemas.users import UserAuditEventPublic, UserCreate, UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

# Full staff directory is admin+supervisor+management; only admin/supervisor
# write, and even between those two the scope differs per-user (see the
# _check_can_manage_target helper below) -- admin can manage anyone, a
# supervisor only operators. Operators see only themselves, via GET
# /auth/me; self-editing your own basic info (handled separately in
# update_user below) doesn't require directory read access.
_read_roles = require_roles(UserRole.admin, UserRole.supervisor, UserRole.management)
_create_delete_roles = require_roles(UserRole.admin, UserRole.supervisor)


def _check_can_manage_target(current_user: User, target: User, new_role: UserRole | None) -> None:
    """Shared scope check for creating/editing/deleting *someone else's*
    account (never called for a user acting on their own record -- that
    path only needs the separate self-role-change guard in update_user).
    Admin can manage any role; a supervisor can only manage -- and can
    only ever set/leave a role as -- operator."""
    if current_user.role == UserRole.admin:
        return
    if current_user.role == UserRole.supervisor:
        if target.role != UserRole.operator:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Supervisors can only manage operator accounts")
        if new_role is not None and new_role != UserRole.operator:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Supervisors cannot set a user's role to anything other than operator"
            )
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this role")


def _record_audit_event(
    db: Session, action: UserAuditAction, actor: User, target: User
) -> None:
    """Snapshot who did what to whom. Names and roles are copied as text
    because a deleted target has no row left to join to -- the trail has to
    outlive the account it describes."""
    db.add(
        UserAuditEvent(
            action=action,
            actor_id=actor.id,
            actor_name=actor.name,
            actor_role=actor.role,
            target_user_id=target.id,
            target_name=target.name,
            target_role=target.role,
        )
    )


@router.get("", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _user=Depends(_read_roles)) -> list[User]:
    return db.query(User).order_by(User.name).all()


@router.get("/audit-events", response_model=list[UserAuditEventPublic])
def list_user_audit_events(
    db: Session = Depends(get_db), _user=Depends(_read_roles)
) -> list[UserAuditEvent]:
    return db.query(UserAuditEvent).order_by(UserAuditEvent.at.desc()).limit(100).all()


@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_read_roles)
) -> User:
    return get_or_404(db, User, user_id, "User not found")


@router.post("", response_model=UserPublic, status_code=201)
def create_user(
    payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(_create_delete_roles)
) -> User:
    if current_user.role == UserRole.supervisor and payload.role != UserRole.operator:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Supervisors can only create operator accounts")

    user = User(
        name=payload.name,
        role=payload.role,
        email=payload.email,
        phone_number=payload.phone_number,
        whatsapp_number=payload.whatsapp_number,
        pin_hash=hash_secret(payload.pin) if payload.pin else None,
        password_hash=hash_secret(payload.password) if payload.password else None,
        created_by_id=current_user.id,
    )
    db.add(user)
    db.flush()
    _record_audit_event(db, UserAuditAction.created, current_user, user)
    commit_or_409(db, "A user with that email or phone number already exists")
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    user = get_or_404(db, User, user_id, "User not found")
    is_self = user.id == current_user.id

    if is_self:
        # Anyone can edit their own basic info (name/phone/email/whatsapp/
        # credential) -- just never their own role, regardless of role held.
        if payload.role is not None and payload.role != current_user.role:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot change your own role")
    else:
        _check_can_manage_target(current_user, user, payload.role)

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
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "operator/supervisor/admin users require a PIN")

    commit_or_409(db, "A user with that email or phone number already exists")
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(_create_delete_roles)
) -> None:
    user = get_or_404(db, User, user_id, "User not found")
    if user.id == current_user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You cannot delete your own account")
    _check_can_manage_target(current_user, user, new_role=None)
    # Recorded before the delete so the snapshot is taken while the row still
    # exists; target_user_id then goes null via ON DELETE SET NULL, leaving the
    # name/role text as the only surviving record of who was removed.
    _record_audit_event(db, UserAuditAction.deleted, current_user, user)
    db.delete(user)
    commit_or_409(db, "Cannot delete a user with existing task, repair, part, or shift-log history")
