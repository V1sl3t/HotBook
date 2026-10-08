"""added email unique logic

Revision ID: 1ba4170e5d10
Revises: 6f912c63ed1b
Create Date: 2024-10-03 21:15:14.329212

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1ba4170e5d10"
down_revision: str | None = "6f912c63ed1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(None, "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("users_email_key", "users", type_="unique")
