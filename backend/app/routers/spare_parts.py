import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import Machine, SparePart, UserRole
from app.schemas.spare_parts import SparePartCreate, SparePartPublic, SparePartUpdate

router = APIRouter(prefix="/spare-parts", tags=["spare_parts"])

# Plant stock is a stores view: management reads it, supervisor and admin
# maintain it. Operators do not get this list — they log a free-text
# replacement on the machine, same as before.
_read_roles = require_roles(UserRole.supervisor, UserRole.management, UserRole.admin)
_write_roles = require_roles(UserRole.supervisor, UserRole.admin)


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _clean_unit(value: str | None) -> str | None:
    text = _clean(value)
    return text or None


def _require_machine(db: Session, machine_id: uuid.UUID | None) -> None:
    if machine_id is None:
        return
    if db.get(Machine, machine_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")


@router.get("", response_model=list[SparePartPublic])
def list_spare_parts(
    search: str | None = None,
    category: str | None = None,
    item_group: str | None = Query(default=None, alias="itemGroup"),
    blank_group: bool = Query(default=False, alias="blankGroup"),
    low_stock: bool = Query(default=False, alias="lowStock"),
    db: Session = Depends(get_db),
    _user=Depends(_read_roles),
) -> list[SparePart]:
    query = db.query(SparePart).options(joinedload(SparePart.machine))
    if search and search.strip():
        query = query.filter(SparePart.name.ilike(f"%{search.strip()}%"))
    if category and category.strip():
        query = query.filter(SparePart.category == category.strip())
    if blank_group:
        query = query.filter(SparePart.item_group == "")
    elif item_group is not None:
        query = query.filter(SparePart.item_group == item_group.strip())
    if low_stock:
        query = query.filter(
            or_(
                SparePart.qty_on_hand <= 0,
                and_(SparePart.min_qty.is_not(None), SparePart.qty_on_hand <= SparePart.min_qty),
            )
        )
    return query.order_by(SparePart.category, SparePart.item_group, SparePart.name).all()


@router.get("/{spare_part_id}", response_model=SparePartPublic)
def get_spare_part(
    spare_part_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(_read_roles),
) -> SparePart:
    part = get_or_404(db, SparePart, spare_part_id, "Spare part not found")
    if part.machine_id is not None:
        _ = part.machine
    return part


@router.post("", response_model=SparePartPublic, status_code=201)
def create_spare_part(
    payload: SparePartCreate,
    db: Session = Depends(get_db),
    _user=Depends(_write_roles),
) -> SparePart:
    _require_machine(db, payload.machine_id)
    name = _clean(payload.name)
    category = _clean(payload.category)
    if not name or not category:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Name and area are required")
    part = SparePart(
        name=name,
        item_group=_clean(payload.item_group),
        category=category,
        qty_on_hand=payload.qty_on_hand,
        unit=_clean_unit(payload.unit),
        min_qty=payload.min_qty,
        machine_id=payload.machine_id,
    )
    db.add(part)
    commit_or_409(db, "A spare with this name, group, and area already exists")
    db.refresh(part)
    return part


@router.patch("/{spare_part_id}", response_model=SparePartPublic)
def update_spare_part(
    spare_part_id: uuid.UUID,
    payload: SparePartUpdate,
    db: Session = Depends(get_db),
    _user=Depends(_write_roles),
) -> SparePart:
    part = get_or_404(db, SparePart, spare_part_id, "Spare part not found")
    changes = payload.model_dump(exclude_unset=True)
    if "machine_id" in changes:
        _require_machine(db, changes["machine_id"])
    if "name" in changes:
        changes["name"] = _clean(changes["name"])
        if not changes["name"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Name is required")
    if "category" in changes:
        changes["category"] = _clean(changes["category"])
        if not changes["category"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Area is required")
    if "item_group" in changes:
        changes["item_group"] = _clean(changes["item_group"])
    if "unit" in changes:
        changes["unit"] = _clean_unit(changes["unit"])
    for field, value in changes.items():
        setattr(part, field, value)
    commit_or_409(db, "A spare with this name, group, and area already exists")
    db.refresh(part)
    return part


@router.delete("/{spare_part_id}", status_code=204)
def delete_spare_part(
    spare_part_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(_write_roles),
) -> None:
    part = get_or_404(db, SparePart, spare_part_id, "Spare part not found")
    db.delete(part)
    commit_or_409(db, "Cannot delete this spare while a part replacement still points at it")
