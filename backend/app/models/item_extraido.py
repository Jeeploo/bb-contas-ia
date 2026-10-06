from __future__ import annotations

from typing import TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


if TYPE_CHECKING:
    from app.models.extracao_inteligente import ExtracaoInteligente


class ItemExtraido(Base):
    __tablename__ = "itens_extraidos"
    __table_args__ = (CheckConstraint("nivel_confianca IS NULL OR (nivel_confianca >= 0 AND nivel_confianca <= 100)", name="ck_item_confianca"),)

    id_item_extraido: Mapped[int] = mapped_column(primary_key=True)
    id_extracao: Mapped[int] = mapped_column(ForeignKey("extracoes_inteligentes.id_extracao"), index=True)
    categoria: Mapped[str] = mapped_column(String)
    descricao_original: Mapped[str] = mapped_column(Text)
    tipo_normalizado: Mapped[str] = mapped_column(String)
    quantidade: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    unidade: Mapped[str | None] = mapped_column(String, nullable=True)
    valor_unitario: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    base_calculo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    aliquota: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    nivel_confianca: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    valor_validado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    situacao_validacao: Mapped[str] = mapped_column(String)
    extracao: Mapped[ExtracaoInteligente] = relationship("ExtracaoInteligente", back_populates="itens_extraidos")
