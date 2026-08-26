import uuid
from datetime import datetime

from pydantic import Field

from app.models import MachineKind
from app.schemas.base import CamelModel


class MachinePersonBrief(CamelModel):
    id: uuid.UUID
    name: str


class MachineCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    operator_id: uuid.UUID | None = None
    supervisor_id: uuid.UUID | None = None
    group_name: str | None = Field(default=None, max_length=255)
    kind: MachineKind = MachineKind.production


class MachineUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = None
    operator_id: uuid.UUID | None = None
    supervisor_id: uuid.UUID | None = None
    group_name: str | None = None
    kind: MachineKind | None = None


class MachineOperatorAssignment(CamelModel):
    machine_id: uuid.UUID
    operator_id: uuid.UUID | None = None


class MachineOperatorAssignmentsUpdate(CamelModel):
    assignments: list[MachineOperatorAssignment] = Field(min_length=1)


class MachineSupervisorAssignment(CamelModel):
    machine_id: uuid.UUID
    supervisor_id: uuid.UUID | None = None


class MachineSupervisorAssignmentsUpdate(CamelModel):
    assignments: list[MachineSupervisorAssignment] = Field(min_length=1)


class MachinePublic(CamelModel):
    id: uuid.UUID
    name: str
    type: str
    location: str | None
    operator_id: uuid.UUID | None = None
    operator: MachinePersonBrief | None = None
    supervisor_id: uuid.UUID | None = None
    supervisor: MachinePersonBrief | None = None
    group_name: str | None = None
    kind: str
    created_at: datetime
