"""add admin role

Revision ID: b926a4cc0bc4
Revises: 7dfe001e88c4
Create Date: 2026-08-20 06:26:49.412961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b926a4cc0bc4'
down_revision: Union[str, None] = '7dfe001e88c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive only -- existing rows/values on the live database are
    # untouched. IF NOT EXISTS makes this safe to re-run.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin'")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE. Reversing this means
    # recreating the enum without 'admin' and recasting the column, which
    # would silently corrupt any row still using 'admin' -- so refuse
    # instead of guessing what to do with those rows.
    conn = op.get_bind()
    admin_count = conn.execute(sa.text("SELECT count(*) FROM users WHERE role = 'admin'")).scalar()
    if admin_count:
        raise RuntimeError(
            f"Cannot downgrade: {admin_count} user(s) still have role='admin'. "
            "Reassign or remove them before downgrading this migration."
        )

    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('operator', 'supervisor', 'management')")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::text::user_role")
    op.execute("DROP TYPE user_role_old")
