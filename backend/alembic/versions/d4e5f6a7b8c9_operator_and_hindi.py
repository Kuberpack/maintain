"""dedicated machine operator and Hindi template fields

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-24 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, tuple[str, ...], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("machines", sa.Column("operator_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_machines_operator_id_users",
        "machines",
        "users",
        ["operator_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint("uq_machines_operator_id", "machines", ["operator_id"])
    op.add_column("task_types", sa.Column("description_hi", sa.Text(), nullable=True))
    op.add_column("checklist_items", sa.Column("section_hi", sa.String(length=255), nullable=True))
    op.add_column("checklist_items", sa.Column("description_hi", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("checklist_items", "description_hi")
    op.drop_column("checklist_items", "section_hi")
    op.drop_column("task_types", "description_hi")
    op.drop_constraint("uq_machines_operator_id", "machines", type_="unique")
    op.drop_constraint("fk_machines_operator_id_users", "machines", type_="foreignkey")
    op.drop_column("machines", "operator_id")
