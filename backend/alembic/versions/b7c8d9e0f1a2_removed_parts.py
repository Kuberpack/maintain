"""removed parts and their movement history

Revision ID: b7c8d9e0f1a2
Revises: a9b8c7d6e5f4
Create Date: 2026-10-26 16:10:00.000000

A part replacement already records the new part fitted. This adds the old
part that came off: condition, where it is now, and the disposition
(repair, refurbished stock, scrap, resale, warranty). Events are append-only.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, tuple[str, ...], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONDITION = ENUM("worn", "damaged", "broken", "reusable", name="removed_part_condition", create_type=False)
_STATUS = ENUM(
    "pending_decision",
    "in_maintenance_store",
    "sent_for_repair",
    "returned_to_stock",
    "scrapped",
    "sold",
    "returned_to_vendor",
    name="removed_part_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text("CREATE TYPE removed_part_condition AS ENUM ('worn', 'damaged', 'broken', 'reusable')"))
    op.execute(
        sa.text(
            "CREATE TYPE removed_part_status AS ENUM ("
            "'pending_decision', 'in_maintenance_store', 'sent_for_repair', "
            "'returned_to_stock', 'scrapped', 'sold', 'returned_to_vendor')"
        )
    )

    op.create_table(
        "removed_parts",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("part_replacement_id", UUID(as_uuid=True), nullable=False),
        sa.Column("machine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("part_name", sa.String(length=255), nullable=False),
        sa.Column("condition", _CONDITION, nullable=False),
        sa.Column("status", _STATUS, nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("vendor", sa.String(length=255), nullable=True),
        sa.Column("sent_on", sa.Date(), nullable=True),
        sa.Column("scrap_on", sa.Date(), nullable=True),
        sa.Column("scrap_qty", sa.Float(), nullable=True),
        sa.Column("scrap_unit", sa.String(length=32), nullable=True),
        sa.Column("scrap_buyer", sa.String(length=255), nullable=True),
        sa.Column("sale_buyer", sa.String(length=255), nullable=True),
        sa.Column("sale_amount", sa.Float(), nullable=True),
        sa.Column("sale_on", sa.Date(), nullable=True),
        sa.Column("warranty_note", sa.Text(), nullable=True),
        sa.Column("stock_credited", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("credited_spare_part_id", UUID(as_uuid=True), nullable=True),
        sa.Column("credited_qty", sa.Integer(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["part_replacement_id"], ["part_replacements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["credited_spare_part_id"], ["spare_parts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("part_replacement_id", name="uq_removed_parts_part_replacement_id"),
    )
    op.create_index("ix_removed_parts_machine_id", "removed_parts", ["machine_id"])
    op.create_index("ix_removed_parts_status", "removed_parts", ["status"])

    op.create_table(
        "removed_part_events",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("removed_part_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", _STATUS, nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_name", sa.String(length=255), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("vendor", sa.String(length=255), nullable=True),
        sa.Column("sent_on", sa.Date(), nullable=True),
        sa.Column("spare_part_id", UUID(as_uuid=True), nullable=True),
        sa.Column("spare_part_name", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("scrap_on", sa.Date(), nullable=True),
        sa.Column("scrap_qty", sa.Float(), nullable=True),
        sa.Column("scrap_unit", sa.String(length=32), nullable=True),
        sa.Column("scrap_buyer", sa.String(length=255), nullable=True),
        sa.Column("sale_buyer", sa.String(length=255), nullable=True),
        sa.Column("sale_amount", sa.Float(), nullable=True),
        sa.Column("sale_on", sa.Date(), nullable=True),
        sa.Column("warranty_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["removed_part_id"], ["removed_parts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["spare_part_id"], ["spare_parts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_removed_part_events_removed_part_id", "removed_part_events", ["removed_part_id"])


def downgrade() -> None:
    op.drop_index("ix_removed_part_events_removed_part_id", table_name="removed_part_events")
    op.drop_table("removed_part_events")
    op.drop_index("ix_removed_parts_status", table_name="removed_parts")
    op.drop_index("ix_removed_parts_machine_id", table_name="removed_parts")
    op.drop_table("removed_parts")
    op.execute(sa.text("DROP TYPE removed_part_status"))
    op.execute(sa.text("DROP TYPE removed_part_condition"))
