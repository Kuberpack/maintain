import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
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


class VendorSpecialty(str, enum.Enum):
    mechanical = "mechanical"
    electrical = "electrical"
    hydraulics = "hydraulics"
    oem = "oem"
    other = "other"


class UserAuditAction(str, enum.Enum):
    created = "created"
    deleted = "deleted"


class OutputUnit(str, enum.Enum):
    kg = "kg"
    pcs = "pcs"


class MachineKind(str, enum.Enum):
    production = "production"
    utility = "utility"


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
    # Which supervisor/admin let this person in. SET NULL rather than RESTRICT:
    # losing the creator's account shouldn't block deleting them, and
    # user_audit_events keeps a name snapshot that survives either delete.
    # Deliberately a bare column, no relationship: every other User-side
    # relationship needs passive_deletes=True to keep the database in charge of
    # FK behavior (see the note above), and nothing reads the creator through
    # the ORM -- the staff directory already has every user loaded by id.
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

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
    shift_logs: Mapped[list["ShiftLog"]] = relationship(
        foreign_keys="ShiftLog.created_by", back_populates="created_by_user", passive_deletes=True
    )
    assigned_machines: Mapped[list["Machine"]] = relationship(
        back_populates="operator", foreign_keys="Machine.operator_id"
    )
    supervised_machines: Mapped[list["Machine"]] = relationship(
        back_populates="supervisor", foreign_keys="Machine.supervisor_id"
    )


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    operator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    supervisor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    group_name: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(20), default=MachineKind.production.value, server_default="production")

    operator: Mapped["User | None"] = relationship(foreign_keys=[operator_id], back_populates="assigned_machines")
    supervisor: Mapped["User | None"] = relationship(foreign_keys=[supervisor_id], back_populates="supervised_machines")
    task_types: Mapped[list["TaskType"]] = relationship(back_populates="machine", cascade="all, delete-orphan")
    part_replacements: Mapped[list["PartReplacement"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    repair_logs: Mapped[list["RepairLog"]] = relationship(back_populates="machine", cascade="all, delete-orphan")
    handover_notes: Mapped[list["HandoverNote"]] = relationship(back_populates="machine", cascade="all, delete-orphan")
    shift_logs: Mapped[list["ShiftLog"]] = relationship(back_populates="machine", cascade="all, delete-orphan")
    vendor_contacts: Mapped[list["VendorContact"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )


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
    # What this will cause if it isn't fixed -- required on new reports so the
    # supervisor can triage without walking to the machine. Nullable in the DB
    # only because rows logged before this column existed have no answer.
    impact: Mapped[str | None] = mapped_column(Text)
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


class VendorContact(Base):
    """Someone outside the company to call when a machine breaks."""

    __tablename__ = "vendor_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    specialty: Mapped[VendorSpecialty] = mapped_column(SAEnum(VendorSpecialty, name="vendor_specialty"))
    phone_number: Mapped[str] = mapped_column(String(20))
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    # Null means plant-wide (any machine), not "unknown".
    machine_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    machine: Mapped["Machine | None"] = relationship(back_populates="vendor_contacts")


class UserAuditEvent(Base):
    """Who let someone in, and who removed them.

    Names and roles are snapshotted as text because a hard-deleted user has
    no row left to join to -- the point of this table is that the trail
    survives the delete it records.
    """

    __tablename__ = "user_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[UserAuditAction] = mapped_column(SAEnum(UserAuditAction, name="user_audit_action"))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_name: Mapped[str] = mapped_column(String(255))
    # users.role owns the user_role type; these columns reuse it, so they must
    # not try to create it (create_type=False is only honored by the
    # postgresql ENUM, not the generic sa.Enum).
    actor_role: Mapped[UserRole] = mapped_column(PGEnum(UserRole, name="user_role", create_type=False))
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    target_name: Mapped[str] = mapped_column(String(255))
    target_role: Mapped[UserRole] = mapped_column(PGEnum(UserRole, name="user_role", create_type=False))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ShiftLog(Base):
    """One row per machine per plant day -- the paper "Machine Start & End
    Time" sheet. Production data, deliberately separate from the corrugator's
    "Shift parameter log" PM checklist (pressures/temperatures)."""

    __tablename__ = "shift_logs"
    __table_args__ = (UniqueConstraint("machine_id", "log_date", name="uq_shift_logs_machine_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE")
    )
    log_date: Mapped[date] = mapped_column(Date)
    # Local (Sonipat) wall-clock times as written on the sheet. A shift that
    # runs past midnight is handled when running hours are computed.
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    output_qty: Mapped[float | None] = mapped_column(Float)
    output_unit: Mapped[OutputUnit] = mapped_column(
        SAEnum(OutputUnit, name="output_unit"), default=OutputUnit.kg, server_default=OutputUnit.kg.value
    )
    job_change_count: Mapped[int | None] = mapped_column(Integer)
    wastage_boardline: Mapped[float | None] = mapped_column(Float)
    wastage_machine: Mapped[float | None] = mapped_column(Float)
    delay_reason: Mapped[str | None] = mapped_column(Text)
    delay_minutes: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    machine: Mapped["Machine"] = relationship(back_populates="shift_logs")
    created_by_user: Mapped["User | None"] = relationship(foreign_keys=[created_by], back_populates="shift_logs")

    @property
    def running_minutes(self) -> int | None:
        """Total running time from the two wall-clock times on the sheet.

        A shift that ends earlier than it started ran past midnight (e.g.
        21:00 to 05:30), so it wraps to the next day rather than going
        negative. Exposed as a property so both the API and the insights view
        read one implementation.
        """
        if self.start_time is None or self.end_time is None:
            return None
        start = self.start_time.hour * 60 + self.start_time.minute
        end = self.end_time.hour * 60 + self.end_time.minute
        return end - start if end >= start else end - start + 24 * 60
