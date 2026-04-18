"""add users and organizations.owner_user_id

Revision ID: d94f567973a1
Revises: c9cd17bad288
Create Date: 2026-04-18 23:38:29.875747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'd94f567973a1'
down_revision: Union[str, None] = 'c9cd17bad288'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.add_column('organizations', sa.Column('owner_user_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_organizations_owner_user_id',
        'organizations', 'users',
        ['owner_user_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_organizations_owner_user_id', 'organizations', ['owner_user_id'])


def downgrade() -> None:
    op.drop_index('ix_organizations_owner_user_id', table_name='organizations')
    op.drop_constraint('fk_organizations_owner_user_id', 'organizations', type_='foreignkey')
    op.drop_column('organizations', 'owner_user_id')
    op.drop_table('users')
