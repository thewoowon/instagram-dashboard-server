"""add organization_memberships table + backfill owners

Revision ID: e1a2b3c4d5e6
Revises: d94f567973a1
Create Date: 2026-04-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "e1a2b3c4d5e6"
down_revision: Union[str, None] = "d94f567973a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default="member"),
        sa.Column("invite_email", sa.String(), nullable=True),
        sa.Column("invite_token", sa.String(), nullable=True),
        sa.Column("invited_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
        sa.UniqueConstraint("invite_token", name="uq_org_invite_token"),
    )
    op.create_index("ix_membership_org", "organization_memberships", ["organization_id"])
    op.create_index("ix_membership_user", "organization_memberships", ["user_id"])

    # Backfill: every existing organization with an owner_user_id gets an 'owner' membership.
    op.execute(
        """
        INSERT INTO organization_memberships (id, organization_id, user_id, role, accepted_at, created_at, updated_at)
        SELECT gen_random_uuid(), id, owner_user_id, 'owner', now(), now(), now()
        FROM organizations
        WHERE owner_user_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_membership_user", table_name="organization_memberships")
    op.drop_index("ix_membership_org", table_name="organization_memberships")
    op.drop_table("organization_memberships")
