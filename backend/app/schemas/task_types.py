import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import TaskCategory


class TaskTypeCreate(BaseModel):
    machine_id: uuid.UUID
    category: TaskCategory
    description: str = Field(min_length=1)
    default_interval_days: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_interval_matches_category(self) -> "TaskTypeCreate":
        if self.category == TaskCategory.repair:
            if self.default_interval_days is not None:
                raise ValueError(
                    "default_interval_days must be omitted for repair (event-driven, not scheduled)"
                )
        elif self.default_interval_days is None:
            raise ValueError("default_interval_days is required for non-repair task types")
        return self


class TaskTypeUpdate(BaseModel):
    category: TaskCategory | None = None
    description: str | None = Field(default=None, min_length=1)
    default_interval_days: int | None = Field(default=None, gt=0)
    # Category/interval consistency is re-checked in the router after merging
    # with the existing row, since a PATCH may only touch one of the two.


class TaskTypePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_id: uuid.UUID
    category: TaskCategory
    description: str
    default_interval_days: int | None
