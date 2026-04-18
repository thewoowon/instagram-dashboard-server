"""add access_token to accounts

Revision ID: 4703ec28ec03
Revises: 1b8f74487487
Create Date: 2026-04-18 21:22:26.031946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4703ec28ec03'
down_revision: Union[str, None] = '1b8f74487487'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('access_token', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'access_token')
