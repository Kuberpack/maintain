"""review status, proof photos, reading ranges, handover notes

Revision ID: c3d4e5f6a7b8
Revises: b926a4cc0bc4
Create Date: 2026-08-24 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
# Merge the two branches that both revised the initial schema:
# a1b2 (PM checklists) and b926 (admin role). Both are already applied
# on production; this revision unifies them and adds review/proof columns.
down_revision: Union[str, tuple[str, ...], None] = ("a1b2c3d4e5f6", "b926a4cc0bc4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("CREATE TYPE review_status AS ENUM ('none', 'awaiting_review', 'approved', 'rejected')"))
    op.execute(sa.text("CREATE TYPE exception_level AS ENUM ('none', 'attention', 'critical')"))

    op.add_column("task_instances", sa.Column("exception_photo_url", sa.String(length=500), nullable=True))
    op.add_column("task_instances", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("task_instances", sa.Column("duration_seconds", sa.Integer(), nullable=True))
    op.add_column(
        "task_instances",
        sa.Column("is_fast_submit", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "task_instances",
        sa.Column(
            "review_status",
            sa.Enum("none", "awaiting_review", "approved", "rejected", name="review_status", create_type=False),
            server_default="none",
            nullable=False,
        ),
    )
    op.add_column("task_instances", sa.Column("reviewed_by", sa.UUID(), nullable=True))
    op.add_column("task_instances", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("task_instances", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column(
        "task_instances",
        sa.Column(
            "exception_level",
            sa.Enum("none", "attention", "critical", name="exception_level", create_type=False),
            server_default="none",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_task_instances_reviewed_by_users",
        "task_instances",
        "users",
        ["reviewed_by"],
        ["id"],
    )
    # Existing completed work already counted as done — treat it as approved so
    # compliance and reopen rules stay consistent after this migration.
    op.execute(sa.text("UPDATE task_instances SET review_status = 'approved' WHERE status = 'done'"))

    op.add_column("checklist_items", sa.Column("min_value", sa.Float(), nullable=True))
    op.add_column("checklist_items", sa.Column("max_value", sa.Float(), nullable=True))

    op.create_table(
        "handover_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("machine_id", sa.UUID(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("handover_notes")
    op.drop_column("checklist_items", "max_value")
    op.drop_column("checklist_items", "min_value")
    op.drop_constraint("fk_task_instances_reviewed_by_users", "task_instances", type_="foreignkey")
    op.drop_column("task_instances", "exception_level")
    op.drop_column("task_instances", "review_notes")
    op.drop_column("task_instances", "reviewed_at")
    op.drop_column("task_instances", "reviewed_by")
    op.drop_column("task_instances", "review_status")
    op.drop_column("task_instances", "is_fast_submit")
    op.drop_column("task_instances", "duration_seconds")
    op.drop_column("task_instances", "started_at")
    op.drop_column("task_instances", "exception_photo_url")
    sa.Enum(name="exception_level").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="review_status").drop(op.get_bind(), checkfirst=True)
