import uuid

from pydantic import Field, model_validator

from app.models import TaskCategory
from app.schemas.base import CamelModel


class TaskTypeCreate(CamelModel):
    machine_id: uuid.UUID
    category: TaskCategory
    description: str = Field(min_length=1)
    default_interval_days: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_interval_matches_category(self) -> "TaskTypeCreate":
        if self.category == TaskCategory.repair:
            if self.default_interval_days is not None:
                raise ValueError(
                    "defaultIntervalDays must be omitted for repair (event-driven, not scheduled)"
                )
        elif self.default_interval_days is None:
            raise ValueError("defaultIntervalDays is required for non-repair task types")
        return self


class TaskTypeUpdate(CamelModel):
    category: TaskCategory | None = None
    description: str | None = Field(default=None, min_length=1)
    default_interval_days: int | None = Field(default=None, gt=0)
    # Category/interval consistency is re-checked in the router after merging
    # with the existing row, since a PATCH may only touch one of the two.


class TaskTypePublic(CamelModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    category: TaskCategory
    description: str
    default_interval_days: int | None
