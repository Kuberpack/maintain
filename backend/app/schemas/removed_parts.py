import uuid
from datetime import date, datetime

from pydantic import Field

from app.models import RemovedPartCondition, RemovedPartStatus
from app.schemas.base import CamelModel


class RemovedPartCapture(CamelModel):
    """What the floor records when the old part comes off.

    Disposition (repair, scrap, sale, warranty, back to stock) is a later
    step. The log only accepts pending or the maintenance store.
    """

    part_name: str | None = Field(default=None, max_length=255)
    condition: RemovedPartCondition = RemovedPartCondition.worn
    status: RemovedPartStatus = RemovedPartStatus.pending_decision
    quantity: int = Field(default=1, ge=1)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    photo_url: str | None = Field(default=None, max_length=512)


class RemovedPartDisposition(CamelModel):
    status: RemovedPartStatus
    condition: RemovedPartCondition | None = None
    notes: str | None = None
    photo_url: str | None = Field(default=None, max_length=512)
    location: str | None = Field(default=None, max_length=255)
    vendor: str | None = Field(default=None, max_length=255)
    sent_on: date | None = None
    spare_part_id: uuid.UUID | None = None
    quantity: int | None = Field(default=None, ge=1)
    scrap_on: date | None = None
    scrap_qty: float | None = Field(default=None, gt=0)
    scrap_unit: str | None = Field(default=None, max_length=32)
    scrap_buyer: str | None = Field(default=None, max_length=255)
    sale_buyer: str | None = Field(default=None, max_length=255)
    sale_amount: float | None = Field(default=None, ge=0)
    sale_on: date | None = None
    warranty_note: str | None = None


class RemovedPartEventPublic(CamelModel):
    id: uuid.UUID
    status: RemovedPartStatus
    actor_id: uuid.UUID | None
    actor_name: str
    at: datetime
    notes: str | None
    photo_url: str | None
    location: str | None
    vendor: str | None
    sent_on: date | None
    spare_part_id: uuid.UUID | None
    spare_part_name: str | None
    quantity: int | None
    scrap_on: date | None
    scrap_qty: float | None
    scrap_unit: str | None
    scrap_buyer: str | None
    sale_buyer: str | None
    sale_amount: float | None
    sale_on: date | None
    warranty_note: str | None


class RemovedPartPublic(CamelModel):
    id: uuid.UUID
    part_replacement_id: uuid.UUID
    machine_id: uuid.UUID
    machine_name: str
    part_name: str
    fitted_part_name: str
    replaced_at: date
    removed_by_name: str | None
    condition: RemovedPartCondition
    status: RemovedPartStatus
    quantity: int
    location: str | None
    notes: str | None
    vendor: str | None
    sent_on: date | None
    scrap_on: date | None
    scrap_qty: float | None
    scrap_unit: str | None
    scrap_buyer: str | None
    sale_buyer: str | None
    sale_amount: float | None
    sale_on: date | None
    warranty_note: str | None
    refurb_spare_name: str | None
    credited_spare_part_id: uuid.UUID | None
    credited_qty: int | None
    age_days: int
    created_at: datetime
    events: list[RemovedPartEventPublic]


class DispositionCount(CamelModel):
    status: RemovedPartStatus
    count: int


class ScrapTotal(CamelModel):
    unit: str
    qty: float


class MonthTotal(CamelModel):
    month: str
    scrap_count: int
    scrap: list[ScrapTotal]
    resale_count: int
    resale_amount: float


class MachineReplacementCount(CamelModel):
    machine_id: uuid.UUID
    machine_name: str
    replacements: int


class RemovedPartsReport(CamelModel):
    by_status: list[DispositionCount]
    pending: int
    pending_older_than_days: int
    stale_days: int
    months: list[MonthTotal]
    machines: list[MachineReplacementCount]
