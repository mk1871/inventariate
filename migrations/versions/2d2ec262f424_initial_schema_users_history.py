"""initial schema (users, history)

Revision ID: 2d2ec262f424
Revises:
Create Date: 2025-09-09 00:31:34.725367
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2d2ec262f424'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password', sa.String(length=128), nullable=False),
        sa.UniqueConstraint('username', name='uq_users_username'),
    )
    # Índice opcional para búsquedas por username (además del unique)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # Crear tabla history
    op.create_table(
        'history',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('month', sa.String(length=20), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Float(), nullable=False),
        sa.Column('date_recorded', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_history_user_id_users'),
    )


def downgrade():
    # Revertir en orden inverso
    op.drop_table('history')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
