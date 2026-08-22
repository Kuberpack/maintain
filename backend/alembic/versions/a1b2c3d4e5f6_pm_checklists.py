"""pm checklists and preventive category

Revision ID: a1b2c3d4e5f6
Revises: 7dfe001e88c4
Create Date: 2026-08-22 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7dfe001e88c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'preventive'"))
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_type_id", sa.UUID(), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requires_value", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("value_unit", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["task_type_id"], ["task_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "checklist_item_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_instance_id", sa.UUID(), nullable=False),
        sa.Column("checklist_item_id", sa.UUID(), nullable=False),
        sa.Column(
            "item_status",
            sa.Enum("ok", "attention", "critical", "planned", name="checklist_item_status"),
            nullable=False,
        ),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["checklist_item_id"], ["checklist_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_instance_id"], ["task_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_instance_id", "checklist_item_id", name="uq_checklist_result_instance_item"),
    )


def downgrade() -> None:
    op.drop_table("checklist_item_results")
    op.drop_table("checklist_items")
    sa.Enum(name="checklist_item_status").drop(op.get_bind(), checkfirst=True)
