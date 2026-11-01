"""Metadados e originais da leitura IA; tentativas independentes de extrações válidas."""
from alembic import op
import sqlalchemy as sa
revision = 'b21d94ca730e'
down_revision = '8bd731c29a10'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('documentos', sa.Column('historico_leitura_ia', sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column('extracoes_inteligentes', sa.Column('metadados_ia', sa.JSON(), nullable=True))
    op.add_column('extracoes_inteligentes', sa.Column('resposta_original_ia', sa.JSON(), nullable=True))
    op.add_column('dados_extraidos', sa.Column('valor_normalizado', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('dados_extraidos', 'valor_normalizado')
    op.drop_column('extracoes_inteligentes', 'resposta_original_ia')
    op.drop_column('extracoes_inteligentes', 'metadados_ia')
    op.drop_column('documentos', 'historico_leitura_ia')
