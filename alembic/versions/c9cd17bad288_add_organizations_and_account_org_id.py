"""add organizations and account.org_id

Revision ID: c9cd17bad288
Revises: 4703ec28ec03
Create Date: 2026-04-18 23:32:35.607319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'c9cd17bad288'
down_revision: Union[str, None] = '4703ec28ec03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('owner_email', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.add_column('accounts', sa.Column('org_id', UUID(as_uuid=True), nullable=True))

    op.execute("""
        INSERT INTO organizations (name, slug, owner_email)
        VALUES ('Mistakr Studio', 'mistakr-studio', 'thewoowon@gmail.com')
    """)
    op.execute("""
        UPDATE accounts
        SET org_id = (SELECT id FROM organizations WHERE slug = 'mistakr-studio')
        WHERE org_id IS NULL
    """)

    op.alter_column('accounts', 'org_id', nullable=False)
    op.create_foreign_key(
        'fk_accounts_org_id',
        'accounts', 'organizations',
        ['org_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_index('ix_accounts_org_id', 'accounts', ['org_id'])


def downgrade() -> None:
    op.drop_index('ix_accounts_org_id', table_name='accounts')
    op.drop_constraint('fk_accounts_org_id', 'accounts', type_='foreignkey')
    op.drop_column('accounts', 'org_id')
    op.drop_table('organizations')
