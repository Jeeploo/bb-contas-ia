"""Aliases determinísticos e atividade cadastral, sem alterar documentos."""
from alembic import op
import sqlalchemy as sa
revision = "f52a90b134cd"
down_revision = "e61d4b902f30"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("concessionarias", sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("concessionaria_aliases",
        sa.Column("id_alias", sa.Integer(), primary_key=True),
        sa.Column("id_concessionaria", sa.Integer(), sa.ForeignKey("concessionarias.id_concessionaria"), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("alias_normalizado", sa.String(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("alias_normalizado", "id_concessionaria", name="uq_alias_concessionaria"))
    op.create_index("ix_concessionaria_aliases_alias_normalizado", "concessionaria_aliases", ["alias_normalizado"])


def downgrade():
    op.drop_table("concessionaria_aliases")
    op.drop_column("concessionarias", "ativo")
