"""candidates table

Revision ID: 0003
Revises: 0002_jobs_celery_task_id
Create Date: 2026-10-04 07:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002_jobs_celery_task_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('candidates',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('source_id', sa.String(length=26), nullable=False),
        sa.Column('event_start', sa.Float(), nullable=False),
        sa.Column('event_end', sa.Float(), nullable=False),
        sa.Column('generators', sa.JSON(), nullable=False),
        sa.Column('reason_codes', sa.JSON(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_source_id'), 'candidates', ['source_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_candidates_source_id'), table_name='candidates')
    op.drop_table('candidates')
