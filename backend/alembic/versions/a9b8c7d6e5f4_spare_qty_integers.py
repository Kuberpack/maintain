"""spare quantities are whole numbers

Revision ID: a9b8c7d6e5f4
Revises: d1e2f3a4b5c6
Create Date: 2026-10-26 12:50:00.000000

The stock sheet stores counts (bearings, metres, packets), but qty was a
float and the replacement form used min=0.001 with step=1. Browsers then
reject 1 and accept 1.001. One log did that: 5 on hand became 3.999.
round() turns that pair back into 1 used and 4 on hand (sheet 5 minus the
one real replacement). Every other stored quantity was already a whole number.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, tuple[str, ...], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "spare_parts",
        "qty_on_hand",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        postgresql_using="round(qty_on_hand)::integer",
    )
    op.alter_column(
        "spare_parts",
        "min_qty",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        postgresql_using="round(min_qty)::integer",
    )
    op.alter_column(
        "part_replacements",
        "quantity_used",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        postgresql_using="round(quantity_used)::integer",
    )


def downgrade() -> None:
    op.alter_column(
        "part_replacements",
        "quantity_used",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        postgresql_using="quantity_used::double precision",
    )
    op.alter_column(
        "spare_parts",
        "min_qty",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        postgresql_using="min_qty::double precision",
    )
    op.alter_column(
        "spare_parts",
        "qty_on_hand",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        postgresql_using="qty_on_hand::double precision",
    )
