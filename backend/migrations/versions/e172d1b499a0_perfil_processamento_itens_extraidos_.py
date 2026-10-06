"""perfil processamento itens extraidos memoria calculo

Revision ID: e172d1b499a0
Revises: 2571aea3edac
Create Date: 2026-10-06 19:30:20.814621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e172d1b499a0'
down_revision: Union[str, Sequence[str], None] = '2571aea3edac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Revisada: somente duas tabelas e duas colunas adicionais.
    op.create_table('perfis_processamento',
    sa.Column('id_perfil', sa.Integer(), nullable=False),
    sa.Column('id_prefixo', sa.Integer(), nullable=False),
    sa.Column('tipo_servico', sa.String(), nullable=False),
    sa.Column('estrategia', sa.String(), nullable=False),
    sa.Column('id_regra', sa.Integer(), nullable=False),
    sa.Column('id_concessionaria', sa.Integer(), nullable=True),
    sa.Column('situacao', sa.String(), nullable=False),
    sa.Column('data_inicio_vigencia', sa.Date(), nullable=False),
    sa.Column('data_fim_vigencia', sa.Date(), nullable=True),
    sa.Column('parametros', sa.JSON(), nullable=False),
    sa.CheckConstraint('data_fim_vigencia IS NULL OR data_fim_vigencia >= data_inicio_vigencia', name='ck_perfil_vigencia'),
    sa.ForeignKeyConstraint(['id_concessionaria'], ['concessionarias.id_concessionaria'], ),
    sa.ForeignKeyConstraint(['id_prefixo'], ['prefixos.id_prefixo'], ),
    sa.ForeignKeyConstraint(['id_regra'], ['regras_calculo.id_regra'], ),
    sa.PrimaryKeyConstraint('id_perfil')
    )
    op.create_index(op.f('ix_perfis_processamento_id_prefixo'), 'perfis_processamento', ['id_prefixo'], unique=False)
    op.create_table('itens_extraidos',
    sa.Column('id_item_extraido', sa.Integer(), nullable=False),
    sa.Column('id_extracao', sa.Integer(), nullable=False),
    sa.Column('categoria', sa.String(), nullable=False),
    sa.Column('descricao_original', sa.Text(), nullable=False),
    sa.Column('tipo_normalizado', sa.String(), nullable=False),
    sa.Column('quantidade', sa.Numeric(precision=18, scale=8), nullable=True),
    sa.Column('unidade', sa.String(), nullable=True),
    sa.Column('valor_unitario', sa.Numeric(precision=18, scale=8), nullable=True),
    sa.Column('valor', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('base_calculo', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('aliquota', sa.Numeric(precision=14, scale=6), nullable=True),
    sa.Column('nivel_confianca', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('valor_validado', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('situacao_validacao', sa.String(), nullable=False),
    sa.CheckConstraint('nivel_confianca IS NULL OR (nivel_confianca >= 0 AND nivel_confianca <= 100)', name='ck_item_confianca'),
    sa.ForeignKeyConstraint(['id_extracao'], ['extracoes_inteligentes.id_extracao'], ),
    sa.PrimaryKeyConstraint('id_item_extraido')
    )
    op.create_index(op.f('ix_itens_extraidos_id_extracao'), 'itens_extraidos', ['id_extracao'], unique=False)
    op.add_column('calculos', sa.Column('memoria_calculo', sa.JSON(), nullable=True))
    op.add_column('itens_regra', sa.Column('obrigatorio', sa.Boolean(), server_default='true', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    # Revisada: somente duas tabelas e duas colunas adicionais.
    op.drop_column('itens_regra', 'obrigatorio')
    op.drop_column('calculos', 'memoria_calculo')
    op.drop_index(op.f('ix_itens_extraidos_id_extracao'), table_name='itens_extraidos')
    op.drop_table('itens_extraidos')
    op.drop_index(op.f('ix_perfis_processamento_id_prefixo'), table_name='perfis_processamento')
    op.drop_table('perfis_processamento')
