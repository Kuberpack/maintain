import uuid
from datetime import date, datetime, time

from pydantic import Field

from app.models import OutputUnit
from app.schemas.base import CamelModel


class ShiftLogUpsert(CamelModel):
    """One row of the paper "Machine Start & End Time" sheet.

    Every production field is optional so an operator can save what they know
    at the start of the shift and finish the row at the end, instead of
    holding the whole thing on paper until everything is filled in.
    """

    machine_id: uuid.UUID
    log_date: date
    start_time: time | None = None
    end_time: time | None = None
    output_qty: float | None = Field(default=None, ge=0)
    output_unit: OutputUnit = OutputUnit.kg
    job_change_count: int | None = Field(default=None, ge=0)
    wastage_boardline: float | None = Field(default=None, ge=0)
    wastage_machine: float | None = Field(default=None, ge=0)
    delay_reason: str | None = None
    delay_minutes: int | None = Field(default=None, ge=0)


class ShiftLogPublic(CamelModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    log_date: date
    start_time: time | None
    end_time: time | None
    output_qty: float | None
    output_unit: OutputUnit
    job_change_count: int | None
    wastage_boardline: float | None
    wastage_machine: float | None
    delay_reason: str | None
    delay_minutes: int | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    # Derived from start/end on the model so the dashboard and any report
    # agree on how a past-midnight shift is counted.
    running_minutes: int | None
