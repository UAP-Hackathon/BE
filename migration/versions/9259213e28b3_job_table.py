"""job table

Revision ID: 9259213e28b3
Revises: ed02177a4c6f
Create Date: 2025-05-06 21:11:33.562100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from database import Base
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9259213e28b3'
down_revision: Union[str, None] = 'ed02177a4c6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('company_name', sa.String(), nullable=False),
    sa.Column('location', sa.String(), nullable=False),
    sa.Column('salary', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('skills', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('experience', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_id'), 'jobs', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_jobs_id'), table_name='jobs')
    op.drop_table('jobs')
    # ### end Alembic commands ###


