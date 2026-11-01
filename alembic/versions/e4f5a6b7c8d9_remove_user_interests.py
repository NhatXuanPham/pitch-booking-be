"""remove_user_interests

Revision ID: e4f5a6b7c8d9
Revises: 6305c5baeb74
Create Date: 2026-11-01 11:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4f5a6b7c8d9'
down_revision = '6305c5baeb74'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('users', 'interests')


def downgrade() -> None:
    op.add_column('users', sa.Column('interests', sa.JSON(), nullable=True))
