"""add_email_verified

Revision ID: 9760d8264812
Revises: 
Create Date: 2026-03-24 11:02:44.821150

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9760d8264812'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'email_verified')
