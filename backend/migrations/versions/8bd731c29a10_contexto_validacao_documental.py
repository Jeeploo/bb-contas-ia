"""Vínculos operacionais e validação documental, sem remover estruturas legadas."""
from alembic import op
import sqlalchemy as sa

revision = "8bd731c29a10"
down_revision = "e172d1b499a0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("usuarios_prefixos",
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuarios.id_usuario"), primary_key=True),
        sa.Column("id_prefixo", sa.Integer(), sa.ForeignKey("prefixos.id_prefixo"), primary_key=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("principal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("NOT principal OR ativo", name="ck_usuario_prefixo_principal_ativo"))
    op.create_index("uq_usuario_prefixo_principal", "usuarios_prefixos", ["id_usuario"], unique=True,
        postgresql_where=sa.text("principal = true AND ativo = true"),
        sqlite_where=sa.text("principal = true AND ativo = true"))
    op.execute(sa.text("""INSERT INTO usuarios_prefixos (id_usuario, id_prefixo, ativo, principal)
        SELECT u.id_usuario, u.id_prefixo, CASE WHEN p.situacao = 'ativo' THEN true ELSE false END,
               CASE WHEN p.situacao = 'ativo' THEN true ELSE false END
        FROM usuarios u JOIN prefixos p ON p.id_prefixo = u.id_prefixo"""))
    op.create_table("unidades_consumidoras",
        sa.Column("id_unidade_consumidora", sa.Integer(), primary_key=True),
        sa.Column("id_prefixo", sa.Integer(), sa.ForeignKey("prefixos.id_prefixo"), nullable=False),
        sa.Column("id_concessionaria", sa.Integer(), sa.ForeignKey("concessionarias.id_concessionaria"), nullable=False),
        sa.Column("unidade_consumidora", sa.String(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("endereco_referencia", sa.String(), nullable=True),
        sa.UniqueConstraint("id_concessionaria", "unidade_consumidora", name="uq_concessionaria_unidade"),
        sa.CheckConstraint("length(trim(unidade_consumidora)) > 0", name="ck_unidade_nao_vazia"))
    op.create_index("ix_unidades_consumidoras_id_prefixo", "unidades_consumidoras", ["id_prefixo"])
    op.add_column("extracoes_inteligentes", sa.Column("resultado_validacao_documental", sa.String(), nullable=False, server_default="EVIDENCIA_INSUFICIENTE"))
    op.add_column("extracoes_inteligentes", sa.Column("motivo_validacao_documental", sa.String(), nullable=True))
    op.add_column("extracoes_inteligentes", sa.Column("evidencias_validacao_documental", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("extracoes_inteligentes", sa.Column("historico_validacao_documental", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    # Batch mantém suporte aos bancos SQLite isolados de teste.
    with op.batch_alter_table("extracoes_inteligentes") as batch:
        batch.add_column(sa.Column("id_usuario_contexto", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("id_prefixo_contexto", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_extracao_usuario_contexto", "usuarios", ["id_usuario_contexto"], ["id_usuario"])
        batch.create_foreign_key("fk_extracao_prefixo_contexto", "prefixos", ["id_prefixo_contexto"], ["id_prefixo"])
        batch.create_check_constraint("ck_resultado_documental", "resultado_validacao_documental IN ('VALIDO', 'DOCUMENTO_NAO_SUPORTADO', 'REGIAO_NAO_SUPORTADA', 'DIVERGENCIA_PREFIXO', 'EVIDENCIA_INSUFICIENTE')")


def downgrade():
    with op.batch_alter_table("extracoes_inteligentes") as batch:
        batch.drop_constraint("ck_resultado_documental", type_="check")
        batch.drop_constraint("fk_extracao_usuario_contexto", type_="foreignkey")
        batch.drop_constraint("fk_extracao_prefixo_contexto", type_="foreignkey")
        for column in ("id_usuario_contexto", "id_prefixo_contexto", "historico_validacao_documental",
                       "evidencias_validacao_documental", "motivo_validacao_documental", "resultado_validacao_documental"):
            batch.drop_column(column)
    op.drop_table("unidades_consumidoras")
    op.drop_table("usuarios_prefixos")
