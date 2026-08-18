import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, enum.Enum):
    operator = "operator"
    supervisor = "supervisor"
    management = "management"


class TaskCategory(str, enum.Enum):
    cleaning = "cleaning"
    oiling = "oiling"
    part_replacement = "part_replacement"
    repair = "repair"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    overdue = "overdue"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    # Login identifier for operator/supervisor (phone + PIN). Deliberately separate from
    # whatsapp_number below: they usually hold the same value in practice, but one is a
    # login credential and the other an alert destination, and they shouldn't be forced
    # to change together.
    phone_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    # Exactly one of pin_hash/password_hash is set, matching role: operator/supervisor use
    # phone+PIN (pin_hash), management uses email+password (password_hash). Enforced in the
    # auth service, not a DB constraint, per "keep it simple."
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    completed_task_instances: Mapped[list["TaskInstance"]] = relationship(
        foreign_keys="TaskInstance.completed_by", back_populates="completed_by_user"
    )
    rescheduled_task_instances: Mapped[list["TaskInstance"]] = relationship(
        foreign_keys="TaskInstance.rescheduled_by", back_populates="rescheduled_by_user"
    )
    part_replacements: Mapped[list["PartReplacement"]] = relationship(
        foreign_keys="PartReplacement.replaced_by", back_populates="replaced_by_user"
    )
    reported_repair_logs: Mapped[list["RepairLog"]] = relationship(
        foreign_keys="RepairLog.reported_by", back_populates="reported_by_user"
    )
    resolved_repair_logs: Mapped[list["RepairLog"]] = relationship(
        foreign_keys="RepairLog.resolved_by", back_populates="resolved_by_user"
    )


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task_types: Mapped[list["TaskType"]] = relationship(back_populates="machine", cascade="all, delete-orphan")
    part_replacements: Mapped[list["PartReplacement"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    repair_logs: Mapped[list["RepairLog"]] = relationship(back_populates="machine", cascade="all, delete-orphan")


class TaskType(Base):
    __tablename__ = "task_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE")
    )
    category: Mapped[TaskCategory] = mapped_column(SAEnum(TaskCategory, name="task_category"))
    description: Mapped[str] = mapped_column(Text)
    # Null for repair: event-driven, not scheduled.
    default_interval_days: Mapped[int | None] = mapped_column(Integer)

    machine: Mapped["Machine"] = relationship(back_populates="task_types")
    task_instances: Mapped[list["TaskInstance"]] = relationship(
        back_populates="task_type", cascade="all, delete-orphan"
    )


class TaskInstance(Base):
    __tablename__ = "task_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_types.id", ondelete="CASCADE")
    )
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status"), default=TaskStatus.pending, server_default=TaskStatus.pending.value
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    rescheduled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    # Camera-capture proof of completion. Column exists now per schema.md; the upload flow
    # isn't wired up until the mark-as-done step is built.
    photo_url: Mapped[str | None] = mapped_column(String(500))

    task_type: Mapped["TaskType"] = relationship(back_populates="task_instances")
    completed_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[completed_by], back_populates="completed_task_instances"
    )
    rescheduled_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[rescheduled_by], back_populates="rescheduled_task_instances"
    )


class PartReplacement(Base):
    __tablename__ = "part_replacements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE")
    )
    part_name: Mapped[str] = mapped_column(String(255))
    replaced_at: Mapped[date] = mapped_column(Date)
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    machine: Mapped["Machine"] = relationship(back_populates="part_replacements")
    replaced_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[replaced_by], back_populates="part_replacements"
    )


class RepairLog(Base):
    __tablename__ = "repair_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE")
    )
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reported_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    issue_description: Mapped[str] = mapped_column(Text)
    downtime_minutes: Mapped[int | None] = mapped_column(Integer)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolution_notes: Mapped[str | None] = mapped_column(Text)

    machine: Mapped["Machine"] = relationship(back_populates="repair_logs")
    reported_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[reported_by], back_populates="reported_repair_logs"
    )
    resolved_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[resolved_by], back_populates="resolved_repair_logs"
    )
