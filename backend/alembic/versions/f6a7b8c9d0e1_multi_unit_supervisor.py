"""one operator on many machines; dedicated supervisor; group and kind

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-26 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, tuple[str, ...], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_machines_operator_id", "machines", type_="unique")
    op.add_column("machines", sa.Column("supervisor_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_machines_supervisor_id_users",
        "machines",
        "users",
        ["supervisor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("machines", sa.Column("group_name", sa.String(length=255), nullable=True))
    op.add_column(
        "machines",
        sa.Column("kind", sa.String(length=20), server_default="production", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("machines", "kind")
    op.drop_column("machines", "group_name")
    op.drop_constraint("fk_machines_supervisor_id_users", "machines", type_="foreignkey")
    op.drop_column("machines", "supervisor_id")
    op.create_unique_constraint("uq_machines_operator_id", "machines", ["operator_id"])
