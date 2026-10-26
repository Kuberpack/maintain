"""spare parts stock

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2
Create Date: 2026-10-26 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, tuple[str, ...], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "spare_parts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("item_group", sa.String(length=255), server_default="", nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("qty_on_hand", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("min_qty", sa.Float(), nullable=True),
        sa.Column("machine_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category", "name", "item_group", name="uq_spare_parts_identity"),
    )
    op.create_index("ix_spare_parts_machine_id", "spare_parts", ["machine_id"])
    op.add_column("part_replacements", sa.Column("spare_part_id", sa.UUID(), nullable=True))
    op.add_column("part_replacements", sa.Column("quantity_used", sa.Float(), nullable=True))
    op.create_foreign_key(
        "fk_part_replacements_spare_part_id",
        "part_replacements",
        "spare_parts",
        ["spare_part_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_part_replacements_spare_part_id", "part_replacements", type_="foreignkey")
    op.drop_column("part_replacements", "quantity_used")
    op.drop_column("part_replacements", "spare_part_id")
    op.drop_index("ix_spare_parts_machine_id", table_name="spare_parts")
    op.drop_table("spare_parts")
