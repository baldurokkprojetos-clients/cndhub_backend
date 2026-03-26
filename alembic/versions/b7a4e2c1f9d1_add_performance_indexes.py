"""add_performance_indexes

Revision ID: b7a4e2c1f9d1
Revises: 9760d8264812
Create Date: 2026-03-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7a4e2c1f9d1'
down_revision: Union[str, None] = '9760d8264812'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_jobs_status_created_at', 'jobs', ['status', 'created_at'], unique=False)
    op.create_index('idx_clientes_hub_id', 'clientes', ['hub_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_clientes_hub_id', table_name='clientes')
    op.drop_index('idx_jobs_status_created_at', table_name='jobs')
