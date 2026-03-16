"""init instagram schema

Revision ID: 1b8f74487487
Revises:
Create Date: 2026-03-16 22:22:35.907455

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON

revision: str = '1b8f74487487'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('brand_name', sa.String(), nullable=False),
        sa.Column('instagram_account_id', sa.String(), nullable=False, unique=True),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('posting_limit_policy', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('brand_rules_json', JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'content_ideas',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('angle', sa.String(), nullable=False, server_default=''),
        sa.Column('priority_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_content_ideas_account_id', 'content_ideas', ['account_id'])

    op.create_table(
        'post_drafts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('idea_id', UUID(as_uuid=True), sa.ForeignKey('content_ideas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('format_type', sa.String(), nullable=False),
        sa.Column('hook', sa.String(), nullable=False, server_default=''),
        sa.Column('caption', sa.String(), nullable=False, server_default=''),
        sa.Column('hashtags', ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('cta', sa.String(), nullable=False, server_default=''),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('quality_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('approval_status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_post_drafts_account_id', 'post_drafts', ['account_id'])
    op.create_index('ix_post_drafts_approval_status', 'post_drafts', ['approval_status'])

    op.create_table(
        'creative_assets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('post_draft_id', UUID(as_uuid=True), sa.ForeignKey('post_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_type', sa.String(), nullable=False),
        sa.Column('storage_url', sa.String(), nullable=False),
        sa.Column('prompt', sa.String(), nullable=False, server_default=''),
        sa.Column('preview_url', sa.String(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_creative_assets_post_draft_id', 'creative_assets', ['post_draft_id'])

    op.create_table(
        'publish_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('post_draft_id', UUID(as_uuid=True), sa.ForeignKey('post_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('publish_status', sa.String(), nullable=False, server_default='queued'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('meta_publish_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_publish_jobs_post_draft_id', 'publish_jobs', ['post_draft_id'])
    op.create_index('ix_publish_jobs_scheduled_at', 'publish_jobs', ['scheduled_at'])

    op.create_table(
        'post_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('post_draft_id', UUID(as_uuid=True), sa.ForeignKey('post_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reach', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('likes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('saves', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shares', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('profile_visits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_post_metrics_post_draft_id', 'post_metrics', ['post_draft_id'])

    # Seed: 계정 2개
    op.execute("""
        INSERT INTO accounts (brand_name, instagram_account_id, brand_rules_json) VALUES
        ('mistakr', 'mistakr_ig_placeholder', '{"tone": "insightful", "forbidden_words": ["무조건", "반드시", "확실히"], "cta_style": "learn", "max_hashtags": 10}'),
        ('100:0lab', '100to0lab_ig_placeholder', '{"tone": "provocative", "forbidden_words": ["법적으로 확정", "100% 과실"], "cta_style": "engage", "max_hashtags": 15}')
    """)


def downgrade() -> None:
    op.drop_table('post_metrics')
    op.drop_table('publish_jobs')
    op.drop_table('creative_assets')
    op.drop_table('post_drafts')
    op.drop_table('content_ideas')
    op.drop_table('accounts')
