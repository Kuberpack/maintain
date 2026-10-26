import uuid

from pydantic import Field

from app.schemas.base import CamelModel


class SparePartCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    item_group: str | None = Field(default=None, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    qty_on_hand: float = Field(ge=0)
    unit: str | None = Field(default=None, max_length=32)
    min_qty: float | None = Field(default=None, ge=0)
    machine_id: uuid.UUID | None = None


class SparePartUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    item_group: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    qty_on_hand: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=32)
    min_qty: float | None = Field(default=None, ge=0)
    machine_id: uuid.UUID | None = None


class SparePartPublic(CamelModel):
    id: uuid.UUID
    name: str
    item_group: str
    category: str
    qty_on_hand: float
    unit: str | None
    min_qty: float | None
    machine_id: uuid.UUID | None
    machine_name: str | None
    low_stock: bool
