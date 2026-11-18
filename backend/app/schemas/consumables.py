import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel

ShiftCode = Literal["A", "B", "C"]


class ConsumableItemCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    item_group: str | None = Field(default=None, max_length=255)
    party_name: str | None = Field(default=None, max_length=255)
    party_address: str | None = Field(default=None, max_length=512)
    contact_no: str | None = Field(default=None, max_length=32)
    lead_time_days: int | None = Field(default=None, ge=0, le=365)
    min_stock: float = Field(default=0, ge=0)
    max_stock: float | None = Field(default=None, ge=0)
    rate: float = Field(default=0, ge=0)
    unit: str = Field(min_length=1, max_length=32)
    qty_on_hand: float = Field(default=0, ge=0)
    tracks_empty_core: bool = False
    standard_qty: float | None = Field(default=None, gt=0)
    standard_per: float | None = Field(default=None, gt=0)
    standard_basis: str | None = Field(default=None, max_length=64)
    active: bool = True


class ConsumableItemUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    item_group: str | None = Field(default=None, max_length=255)
    party_name: str | None = Field(default=None, max_length=255)
    party_address: str | None = Field(default=None, max_length=512)
    contact_no: str | None = Field(default=None, max_length=32)
    lead_time_days: int | None = Field(default=None, ge=0, le=365)
    min_stock: float | None = Field(default=None, ge=0)
    max_stock: float | None = Field(default=None, ge=0)
    rate: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    tracks_empty_core: bool | None = None
    standard_qty: float | None = Field(default=None, gt=0)
    standard_per: float | None = Field(default=None, gt=0)
    standard_basis: str | None = Field(default=None, max_length=64)
    active: bool | None = None
    clear_standard: bool = False
    clear_max_stock: bool = False


class ConsumableItemPublic(CamelModel):
    id: uuid.UUID
    name: str
    item_group: str
    party_name: str | None
    party_address: str | None
    contact_no: str | None
    lead_time_days: int | None
    min_stock: float
    max_stock: float | None
    rate: float
    unit: str
    qty_on_hand: float
    low_stock: bool
    tracks_empty_core: bool
    cores_outstanding: int
    standard_qty: float | None
    standard_per: float | None
    standard_basis: str | None
    active: bool


class InwardCreate(CamelModel):
    qty: float = Field(gt=0)
    received_on: date | None = None
    note: str | None = Field(default=None, max_length=500)


class StockCountCreate(CamelModel):
    counted_qty: float = Field(ge=0)
    counted_on: date | None = None
    note: str | None = Field(default=None, max_length=500)


class StockCountPublic(CamelModel):
    id: uuid.UUID
    item_id: uuid.UUID
    book_qty: float
    counted_qty: float
    variance: float
    note: str | None
    counted_by_name: str
    counted_on: date


class SlipLineIn(CamelModel):
    item_id: uuid.UUID
    qty: float = Field(gt=0)


class SlipCreate(CamelModel):
    slip_date: date
    shift: ShiftCode
    department: str = Field(min_length=1, max_length=255)
    machine_id: uuid.UUID
    received_by_id: uuid.UUID
    hod_name: str | None = Field(default=None, max_length=255)
    remark: str | None = None
    lines: list[SlipLineIn] = Field(min_length=1)
    override_missing_cores: bool = False


class ReturnCreate(CamelModel):
    qty: float = Field(gt=0)
    returned_on: date | None = None
    note: str | None = Field(default=None, max_length=500)


class CloseLineIn(CamelModel):
    qty_used: float = Field(ge=0)
    qty_returned: float = Field(ge=0)
    qty_carried: float = Field(ge=0)
    production_qty: float | None = Field(default=None, ge=0)
    leakage_note: str | None = Field(default=None, max_length=1000)


class LineNoteIn(CamelModel):
    line_id: uuid.UUID
    leakage_note: str = Field(min_length=1, max_length=1000)


class ConfirmSlipIn(CamelModel):
    note: str | None = Field(default=None, max_length=1000)
    line_notes: list[LineNoteIn] = Field(default_factory=list)


class ReturnPublic(CamelModel):
    id: uuid.UUID
    qty: float
    note: str | None
    returned_by_name: str
    returned_on: date


class SlipLinePublic(CamelModel):
    id: uuid.UUID
    line_no: int
    item_id: uuid.UUID
    item_name: str
    unit: str
    rate: float
    qty_issued: float
    qty_used: float | None
    qty_returned: float
    qty_carried: float | None
    leakage_qty: float | None
    leakage_value: float | None
    balance_status: str
    leakage_note: str | None
    production_qty: float | None
    expected_qty: float | None
    variance_pct: float | None
    standard_qty: float | None
    standard_per: float | None
    standard_basis: str | None
    core_due: bool
    core_returned: bool
    closed_at: datetime | None
    returns: list[ReturnPublic]


class SlipPublic(CamelModel):
    id: uuid.UUID
    financial_year: str
    slip_no: int
    slip_no_label: str
    slip_date: date
    shift: str
    department: str
    machine_id: uuid.UUID
    machine_name: str
    issued_by_id: uuid.UUID | None
    issued_by_name: str
    received_by_id: uuid.UUID | None
    received_by_name: str
    hod_name: str | None
    remark: str | None
    supervisor_confirmed_at: datetime | None
    supervisor_confirmed_name: str | None
    supervisor_note: str | None
    status: str
    stale: bool
    has_leakage: bool
    needs_sign: bool
    leakage_qty: float
    leakage_value: float
    lines: list[SlipLinePublic]
    created_at: datetime


class SlipCreated(CamelModel):
    slip: SlipPublic
    core_warnings: list[str]


class ShiftInfo(CamelModel):
    id: str
    label: str
    starts: str
    ends: str


class ConsumablePolicyPublic(CamelModel):
    core_policy: str
    shifts: list[ShiftInfo]


class LeakageBucket(CamelModel):
    key: str
    label: str
    qty: float
    value_inr: float
    variance_pct: float | None = None


class MonthBucket(CamelModel):
    month: str
    qty: float
    value_inr: float


class StaleSlipRow(CamelModel):
    id: uuid.UUID
    slip_no_label: str
    financial_year: str
    slip_date: date
    shift: str
    department: str
    machine_name: str
    received_by_name: str
    issued_by_name: str


class LeakageReport(CamelModel):
    month: str
    total_qty: float
    total_value_inr: float
    by_item: list[LeakageBucket]
    by_machine: list[LeakageBucket]
    by_operator: list[LeakageBucket]
    by_month: list[MonthBucket]
    top_items: list[LeakageBucket]
    stale_slips: list[StaleSlipRow]


class DailyDay(CamelModel):
    day: int
    inward: float
    consumption: float


class DailyItemRow(CamelModel):
    item_id: uuid.UUID
    item_name: str
    item_group: str
    party_name: str | None
    party_address: str | None
    contact_no: str | None
    lead_time_days: int | None
    min_stock: float
    max_stock: float | None
    rate: float
    opening_stock: float
    unit: str
    days: list[DailyDay]
    month_inward: float
    month_consumption: float
    closing_stock: float


class DailySheet(CamelModel):
    month: str
    days_in_month: int
    rows: list[DailyItemRow]
