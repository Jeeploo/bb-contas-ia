"""Referência aditiva de storage por documento; sem mover ou apagar arquivos."""
from alembic import op
import sqlalchemy as sa
revision = 'e61d4b902f30'
down_revision = 'd45f3a21b001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('documentos', sa.Column('storage_provider', sa.String(16), nullable=False, server_default='local'))
    op.add_column('documentos', sa.Column('storage_key', sa.String(), nullable=True))
    # Preserva a referência antiga exatamente como está; não acessa filesystem/R2.
    op.execute(sa.text('UPDATE documentos SET storage_key = caminho_arquivo WHERE storage_key IS NULL'))


def downgrade():
    # R2 não pode ser reinterpretado como arquivo local por uma versão antiga.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT COUNT(*) FROM documentos WHERE storage_provider <> 'local'")):
        raise RuntimeError('Downgrade bloqueado: existem documentos em storage externo')
    op.drop_column('documentos', 'storage_key')
    op.drop_column('documentos', 'storage_provider')
