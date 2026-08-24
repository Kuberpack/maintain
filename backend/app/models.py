import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, enum.Enum):
    operator = "operator"
    supervisor = "supervisor"
    management = "management"
    admin = "admin"


class TaskCategory(str, enum.Enum):
    cleaning = "cleaning"
    oiling = "oiling"
    part_replacement = "part_replacement"
    repair = "repair"
    preventive = "preventive"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    overdue = "overdue"


class ChecklistItemStatus(str, enum.Enum):
    ok = "ok"
    attention = "attention"
    critical = "critical"
    planned = "planned"


class ReviewStatus(str, enum.Enum):
    none = "none"
    awaiting_review = "awaiting_review"
    approved = "approved"
    rejected = "rejected"


class ExceptionLevel(str, enum.Enum):
    none = "none"
    attention = "attention"
    critical = "critical"


class ReviewStatus(str, enum.Enum):
    none = "none"
    awaiting_review = "awaiting_review"
    approved = "approved"
    rejected = "rejected"


class ExceptionLevel(str, enum.Enum):
    none = "none"
    attention = "attention"
    critical = "critical"


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

    # passive_deletes=True on all five: without it, SQLAlchemy's default
    # ORM-level delete behavior loads these collections and proactively sets
    # their (nullable) FK columns to NULL before deleting the user -- silently
    # wiping audit-trail attribution instead of letting the database's
    # RESTRICT constraint reject the delete. passive_deletes defers entirely
    # to the database's FK behavior.
    completed_task_instances: Mapped[list["TaskInstance"]] = relationship(
        foreign_keys="TaskInstance.completed_by", back_populates="completed_by_user", passive_deletes=True
    )
    rescheduled_task_instances: Mapped[list["TaskInstance"]] = relationship(
        foreign_keys="TaskInstance.rescheduled_by", back_populates="rescheduled_by_user", passive_deletes=True
    )
    reviewed_task_instances: Mapped[list["TaskInstance"]] = relationship(
        foreign_keys="TaskInstance.reviewed_by", back_populates="reviewed_by_user", passive_deletes=True
    )
    part_replacements: Mapped[list["PartReplacement"]] = relationship(
        foreign_keys="PartReplacement.replaced_by", back_populates="replaced_by_user", passive_deletes=True
    )
    reported_repair_logs: Mapped[list["RepairLog"]] = relationship(
        foreign_keys="RepairLog.reported_by", back_populates="reported_by_user", passive_deletes=True
    )
    resolved_repair_logs: Mapped[list["RepairLog"]] = relationship(
        foreign_keys="RepairLog.resolved_by", back_populates="resolved_by_user", passive_deletes=True
    )
    handover_notes: Mapped[list["HandoverNote"]] = relationship(
        foreign_keys="HandoverNote.created_by", back_populates="created_by_user", passive_deletes=True
    )
    assigned_machine: Mapped["Machine | None"] = relationship(
        back_populates="operator", uselist=False, foreign_keys="Machine.operator_id"
    )


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    operator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), unique=True
    )

    operator: Mapped["User | None"] = relationship(foreign_keys=[operator_id], back_populates="assigned_machine")
    task_types: Mapped[list["TaskType"]] = relationship(back_populates="machine", cascade="all, delete-orphan")
    part_replacements: Mapped[list["PartReplacement"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    repair_logs: Mapped[list["RepairLog"]] = relationship(back_populates="machine", cascade="all, delete-orphan")
    handover_notes: Mapped[list["HandoverNote"]] = relationship(back_populates="machine", cascade="all, delete-orphan")


class TaskType(Base):
    __tablename__ = "task_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE")
    )
    category: Mapped[TaskCategory] = mapped_column(SAEnum(TaskCategory, name="task_category"))
    description: Mapped[str] = mapped_column(Text)
    description_hi: Mapped[str | None] = mapped_column(Text)
    # Null for repair: event-driven, not scheduled.
    default_interval_days: Mapped[int | None] = mapped_column(Integer)

    machine: Mapped["Machine"] = relationship(back_populates="task_types")
    task_instances: Mapped[list["TaskInstance"]] = relationship(
        back_populates="task_type", cascade="all, delete-orphan"
    )
    checklist_items: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="task_type", cascade="all, delete-orphan", order_by="ChecklistItem.sort_order"
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
    photo_url: Mapped[str | None] = mapped_column(String(500))
    exception_photo_url: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    is_fast_submit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    review_status: Mapped[ReviewStatus] = mapped_column(
        SAEnum(ReviewStatus, name="review_status"),
        default=ReviewStatus.none,
        server_default=ReviewStatus.none.value,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(Text)
    exception_level: Mapped[ExceptionLevel] = mapped_column(
        SAEnum(ExceptionLevel, name="exception_level"),
        default=ExceptionLevel.none,
        server_default=ExceptionLevel.none.value,
    )

    task_type: Mapped["TaskType"] = relationship(back_populates="task_instances")
    completed_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[completed_by], back_populates="completed_task_instances"
    )
    rescheduled_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[rescheduled_by], back_populates="rescheduled_task_instances"
    )
    reviewed_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[reviewed_by], back_populates="reviewed_task_instances"
    )
    checklist_item_results: Mapped[list["ChecklistItemResult"]] = relationship(
        back_populates="task_instance", cascade="all, delete-orphan"
    )


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_types.id", ondelete="CASCADE")
    )
    section: Mapped[str] = mapped_column(String(255))
    section_hi: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    description_hi: Mapped[str | None] = mapped_column(Text)
    requires_value: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    value_unit: Mapped[str | None] = mapped_column(String(50))
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)

    task_type: Mapped["TaskType"] = relationship(back_populates="checklist_items")
    results: Mapped[list["ChecklistItemResult"]] = relationship(
        back_populates="checklist_item", cascade="all, delete-orphan"
    )


class ChecklistItemResult(Base):
    __tablename__ = "checklist_item_results"
    __table_args__ = (UniqueConstraint("task_instance_id", "checklist_item_id", name="uq_checklist_result_instance_item"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_instances.id", ondelete="CASCADE")
    )
    checklist_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checklist_items.id", ondelete="CASCADE")
    )
    item_status: Mapped[ChecklistItemStatus] = mapped_column(
        SAEnum(ChecklistItemStatus, name="checklist_item_status")
    )
    numeric_value: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    task_instance: Mapped["TaskInstance"] = relationship(back_populates="checklist_item_results")
    checklist_item: Mapped["ChecklistItem"] = relationship(back_populates="results")


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


class HandoverNote(Base):
    __tablename__ = "handover_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE")
    )
    note: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    machine: Mapped["Machine"] = relationship(back_populates="handover_notes")
    created_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[created_by], back_populates="handover_notes"
    )
