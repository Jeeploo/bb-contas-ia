from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.prefixo import Prefixo
    from app.models.concessionaria import Concessionaria
    from app.models.documento import Documento


class ContaConsumo(Base):
    __tablename__ = "contas_consumo"

    id_conta: Mapped[int] = mapped_column(primary_key=True)
    numero_conta: Mapped[str | None] = mapped_column(String, nullable=True)
    competencia: Mapped[str] = mapped_column(String, nullable=False)
    data_emissao: Mapped[date | None] = mapped_column(nullable=True)
    data_vencimento: Mapped[date] = mapped_column(nullable=False)
    valor_original: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    codigo_barras: Mapped[str | None] = mapped_column(String, nullable=True)
    consumo: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    unidade_consumo: Mapped[str | None] = mapped_column(String, nullable=True)
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    situacao: Mapped[str] = mapped_column(String, nullable=False)
    id_prefixo: Mapped[int] = mapped_column(
        ForeignKey("prefixos.id_prefixo"), nullable=False
    )
    id_concessionaria: Mapped[int] = mapped_column(
        ForeignKey("concessionarias.id_concessionaria"), nullable=False
    )

    prefixo: Mapped[Prefixo] = relationship(back_populates="contas")
    concessionaria: Mapped[Concessionaria] = relationship(back_populates="contas")
    documentos: Mapped[list[Documento]] = relationship(back_populates="conta")
