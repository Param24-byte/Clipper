"""clips table

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-04 07:36:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('clips',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('source_id', sa.String(length=26), nullable=False),
        sa.Column('project_id', sa.String(length=26), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('candidate_ids', sa.JSON(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clips_project_id'), 'clips', ['project_id'], unique=False)
    op.create_index(op.f('ix_clips_source_id'), 'clips', ['source_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_clips_source_id'), table_name='clips')
    op.drop_index(op.f('ix_clips_project_id'), table_name='clips')
    op.drop_table('clips')
