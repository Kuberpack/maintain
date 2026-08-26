"""vendor contacts, user audit trail, shift logs, repair impact

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-26 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, tuple[str, ...], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The types are created explicitly below, so every column reference has to be
# postgresql.ENUM with create_type=False. The generic sa.Enum silently ignores
# that flag and makes create_table emit its own CREATE TYPE, which fails as a
# duplicate -- and would try to re-create the long-existing user_role type.
_SPECIALTY = ENUM("mechanical", "electrical", "hydraulics", "oem", "other", name="vendor_specialty", create_type=False)
_AUDIT_ACTION = ENUM("created", "deleted", name="user_audit_action", create_type=False)
_OUTPUT_UNIT = ENUM("kg", "pcs", name="output_unit", create_type=False)
_USER_ROLE = ENUM("operator", "supervisor", "management", "admin", name="user_role", create_type=False)


def upgrade() -> None:
    op.execute(
        sa.text("CREATE TYPE vendor_specialty AS ENUM ('mechanical', 'electrical', 'hydraulics', 'oem', 'other')")
    )
    op.execute(sa.text("CREATE TYPE user_audit_action AS ENUM ('created', 'deleted')"))
    op.execute(sa.text("CREATE TYPE output_unit AS ENUM ('kg', 'pcs')"))

    op.create_table(
        "vendor_contacts",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("specialty", _SPECIALTY, nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("whatsapp_number", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("machine_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_audit_events",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("action", _AUDIT_ACTION, nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_name", sa.String(length=255), nullable=False),
        sa.Column("actor_role", _USER_ROLE, nullable=False),
        sa.Column("target_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("target_name", sa.String(length=255), nullable=False),
        sa.Column("target_role", _USER_ROLE, nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "shift_logs",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("machine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("output_qty", sa.Float(), nullable=True),
        sa.Column("output_unit", _OUTPUT_UNIT, server_default="kg", nullable=False),
        sa.Column("job_change_count", sa.Integer(), nullable=True),
        sa.Column("wastage_boardline", sa.Float(), nullable=True),
        sa.Column("wastage_machine", sa.Float(), nullable=True),
        sa.Column("delay_reason", sa.Text(), nullable=True),
        sa.Column("delay_minutes", sa.Integer(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("machine_id", "log_date", name="uq_shift_logs_machine_date"),
    )

    op.add_column("repair_logs", sa.Column("impact", sa.Text(), nullable=True))

    op.add_column("users", sa.Column("created_by_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_users_created_by_id_users",
        "users",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_created_by_id_users", "users", type_="foreignkey")
    op.drop_column("users", "created_by_id")
    op.drop_column("repair_logs", "impact")
    op.drop_table("shift_logs")
    op.drop_table("user_audit_events")
    op.drop_table("vendor_contacts")
    # Alembic's drop_table doesn't drop native Postgres enum types, so a
    # downgrade/upgrade cycle would fail on the next CREATE TYPE without this.
    sa.Enum(name="output_unit").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_audit_action").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="vendor_specialty").drop(op.get_bind(), checkfirst=True)
