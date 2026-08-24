import uuid

from app.models import ChecklistItemStatus
from app.schemas.base import CamelModel


class ChecklistItemPublic(CamelModel):
    id: uuid.UUID
    task_type_id: uuid.UUID
    section: str
    sort_order: int
    description: str
    requires_value: bool
    value_unit: str | None
    min_value: float | None
    max_value: float | None


class ChecklistItemResultInput(CamelModel):
    checklist_item_id: uuid.UUID
    item_status: ChecklistItemStatus
    numeric_value: float | None = None
    notes: str | None = None


class ChecklistItemResultPublic(CamelModel):
    id: uuid.UUID
    task_instance_id: uuid.UUID
    checklist_item_id: uuid.UUID
    item_status: ChecklistItemStatus
    numeric_value: float | None
    notes: str | None
