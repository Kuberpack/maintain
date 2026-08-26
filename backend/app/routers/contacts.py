import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import Machine, UserRole, VendorContact
from app.schemas.vendor_contacts import (
    VendorContactCreate,
    VendorContactPublic,
    VendorContactUpdate,
)

router = APIRouter(prefix="/vendor-contacts", tags=["vendor_contacts"])

# Every role reads this, operators included -- the whole point is that the
# person standing at a broken machine can call for help without asking
# anyone first. Only supervisor+admin maintain the list.
_write_roles = require_roles(UserRole.supervisor, UserRole.admin)


@router.get("", response_model=list[VendorContactPublic])
def list_vendor_contacts(
    machine_id: uuid.UUID | None = Query(default=None, alias="machineId"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[VendorContact]:
    query = db.query(VendorContact)
    if machine_id is not None:
        # Plant-wide contacts are relevant to every machine, so they stay in
        # the result rather than being filtered out by a machine filter.
        query = query.filter(
            (VendorContact.machine_id == machine_id) | (VendorContact.machine_id.is_(None))
        )
    return query.order_by(VendorContact.specialty, VendorContact.name).all()


@router.get("/{contact_id}", response_model=VendorContactPublic)
def get_vendor_contact(
    contact_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> VendorContact:
    return get_or_404(db, VendorContact, contact_id, "Contact not found")


@router.post("", response_model=VendorContactPublic, status_code=201)
def create_vendor_contact(
    payload: VendorContactCreate, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> VendorContact:
    if payload.machine_id is not None:
        get_or_404(db, Machine, payload.machine_id, "Machine not found")
    contact = VendorContact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.patch("/{contact_id}", response_model=VendorContactPublic)
def update_vendor_contact(
    contact_id: uuid.UUID,
    payload: VendorContactUpdate,
    db: Session = Depends(get_db),
    _user=Depends(_write_roles),
) -> VendorContact:
    contact = get_or_404(db, VendorContact, contact_id, "Contact not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("machine_id") is not None:
        get_or_404(db, Machine, changes["machine_id"], "Machine not found")
    for field, value in changes.items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_vendor_contact(
    contact_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> None:
    contact = get_or_404(db, VendorContact, contact_id, "Contact not found")
    db.delete(contact)
    commit_or_409(db, "Cannot delete this contact")
