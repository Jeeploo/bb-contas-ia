"""Credenciais DEMO protegidas e sessões revogáveis."""
from alembic import op
import sqlalchemy as sa
revision = 'd45f3a21b001'
down_revision = 'c31f82a104df'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('credenciais_demo',
        sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('usuarios.id_usuario'), primary_key=True),
        sa.Column('senha_hash', sa.String(), nullable=False),
        sa.Column('fator_hash', sa.String(), nullable=False))
    op.create_table('sessoes_demo',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('usuarios.id_usuario'), nullable=False),
        sa.Column('id_prefixo', sa.Integer(), sa.ForeignKey('prefixos.id_prefixo'), nullable=True),
        sa.Column('expira_em', sa.DateTime(), nullable=False))
    op.create_index('ix_sessoes_demo_id_usuario', 'sessoes_demo', ['id_usuario'])


def downgrade():
    op.drop_table('sessoes_demo')
    op.drop_table('credenciais_demo')
