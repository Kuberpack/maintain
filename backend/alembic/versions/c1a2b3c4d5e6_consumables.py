"""consumables: item master, store issue slips, returns, counts

Revision ID: c1a2b3c4d5e6
Revises: b7c8d9e0f1a2
Create Date: 2026-11-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1a2b3c4d5e6"
down_revision: Union[str, tuple[str, ...], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consumable_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("item_group", sa.String(length=255), server_default="", nullable=False),
        sa.Column("party_name", sa.String(length=255), nullable=True),
        sa.Column("party_address", sa.String(length=512), nullable=True),
        sa.Column("contact_no", sa.String(length=32), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("min_stock", sa.Float(), server_default="0", nullable=False),
        sa.Column("max_stock", sa.Float(), nullable=True),
        sa.Column("rate", sa.Float(), server_default="0", nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("qty_on_hand", sa.Float(), server_default="0", nullable=False),
        sa.Column("tracks_empty_core", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("cores_outstanding", sa.Integer(), server_default="0", nullable=False),
        sa.Column("standard_qty", sa.Float(), nullable=True),
        sa.Column("standard_per", sa.Float(), nullable=True),
        sa.Column("standard_basis", sa.String(length=64), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "consumable_slip_counters",
        sa.Column("financial_year", sa.String(length=7), nullable=False),
        sa.Column("last_number", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("financial_year"),
    )
    op.create_table(
        "consumable_slips",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("financial_year", sa.String(length=7), nullable=False),
        sa.Column("slip_no", sa.Integer(), nullable=False),
        sa.Column("slip_date", sa.Date(), nullable=False),
        sa.Column("shift", sa.String(length=1), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=False),
        sa.Column("machine_id", sa.UUID(), nullable=False),
        sa.Column("machine_name", sa.String(length=255), nullable=False),
        sa.Column("issued_by_id", sa.UUID(), nullable=True),
        sa.Column("issued_by_name", sa.String(length=255), nullable=False),
        sa.Column("received_by_id", sa.UUID(), nullable=True),
        sa.Column("received_by_name", sa.String(length=255), nullable=False),
        sa.Column("hod_name", sa.String(length=255), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("supervisor_confirmed_by_id", sa.UUID(), nullable=True),
        sa.Column("supervisor_confirmed_name", sa.String(length=255), nullable=True),
        sa.Column("supervisor_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supervisor_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["issued_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["received_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supervisor_confirmed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("financial_year", "slip_no", name="uq_consumable_slips_fy_no"),
    )
    op.create_index("ix_consumable_slips_machine_id", "consumable_slips", ["machine_id"])
    op.create_index("ix_consumable_slips_received_by_id", "consumable_slips", ["received_by_id"])
    op.create_index("ix_consumable_slips_slip_date", "consumable_slips", ["slip_date"])
    op.create_table(
        "consumable_slip_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slip_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("qty_issued", sa.Float(), nullable=False),
        sa.Column("qty_returned", sa.Float(), server_default="0", nullable=False),
        sa.Column("qty_used", sa.Float(), nullable=True),
        sa.Column("qty_carried", sa.Float(), nullable=True),
        sa.Column("leakage_note", sa.Text(), nullable=True),
        sa.Column("production_qty", sa.Float(), nullable=True),
        sa.Column("expected_qty", sa.Float(), nullable=True),
        sa.Column("variance_pct", sa.Float(), nullable=True),
        sa.Column("core_due", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("core_returned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("core_returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("core_returned_by_id", sa.UUID(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["slip_id"], ["consumable_slips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["consumable_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["core_returned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consumable_slip_lines_slip_id", "consumable_slip_lines", ["slip_id"])
    op.create_index("ix_consumable_slip_lines_item_id", "consumable_slip_lines", ["item_id"])
    op.create_table(
        "consumable_returns",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("line_id", sa.UUID(), nullable=False),
        sa.Column("qty", sa.Float(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("returned_by_id", sa.UUID(), nullable=True),
        sa.Column("returned_by_name", sa.String(length=255), nullable=False),
        sa.Column("returned_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["line_id"], ["consumable_slip_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["returned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consumable_returns_line_id", "consumable_returns", ["line_id"])
    op.create_table(
        "consumable_moves",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("qty_delta", sa.Float(), nullable=False),
        sa.Column("moved_on", sa.Date(), nullable=False),
        sa.Column("line_id", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["consumable_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["line_id"], ["consumable_slip_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consumable_moves_item_day", "consumable_moves", ["item_id", "moved_on"])
    op.create_table(
        "consumable_counts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("book_qty", sa.Float(), nullable=False),
        sa.Column("counted_qty", sa.Float(), nullable=False),
        sa.Column("variance", sa.Float(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("counted_by_id", sa.UUID(), nullable=True),
        sa.Column("counted_by_name", sa.String(length=255), nullable=False),
        sa.Column("counted_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["consumable_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["counted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consumable_counts_item_id", "consumable_counts", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_consumable_counts_item_id", table_name="consumable_counts")
    op.drop_table("consumable_counts")
    op.drop_index("ix_consumable_moves_item_day", table_name="consumable_moves")
    op.drop_table("consumable_moves")
    op.drop_index("ix_consumable_returns_line_id", table_name="consumable_returns")
    op.drop_table("consumable_returns")
    op.drop_index("ix_consumable_slip_lines_item_id", table_name="consumable_slip_lines")
    op.drop_index("ix_consumable_slip_lines_slip_id", table_name="consumable_slip_lines")
    op.drop_table("consumable_slip_lines")
    op.drop_index("ix_consumable_slips_slip_date", table_name="consumable_slips")
    op.drop_index("ix_consumable_slips_received_by_id", table_name="consumable_slips")
    op.drop_index("ix_consumable_slips_machine_id", table_name="consumable_slips")
    op.drop_table("consumable_slips")
    op.drop_table("consumable_slip_counters")
    op.drop_table("consumable_items")
