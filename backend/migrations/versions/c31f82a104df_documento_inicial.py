"""Documento como entrada inicial, com contexto independente de ContaConsumo."""
from alembic import op
import sqlalchemy as sa
revision = 'c31f82a104df'
down_revision = 'b21d94ca730e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('documentos') as batch:
        batch.alter_column('id_conta', existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column('id_prefixo_contexto', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('id_usuario_contexto', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_documento_prefixo_contexto', 'prefixos', ['id_prefixo_contexto'], ['id_prefixo'])
        batch.create_foreign_key('fk_documento_usuario_contexto', 'usuarios', ['id_usuario_contexto'], ['id_usuario'])


def downgrade():
    # Documentos pendentes precisam ser resolvidos antes de retornar ao modelo legado.
    with op.batch_alter_table('documentos') as batch:
        batch.drop_constraint('fk_documento_usuario_contexto', type_='foreignkey')
        batch.drop_constraint('fk_documento_prefixo_contexto', type_='foreignkey')
        batch.drop_column('id_usuario_contexto')
        batch.drop_column('id_prefixo_contexto')
        batch.alter_column('id_conta', existing_type=sa.Integer(), nullable=False)
