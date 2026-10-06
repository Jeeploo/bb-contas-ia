from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.regra_calculo import RegraCalculo


class ItemRegra(Base):
    __tablename__ = "itens_regra"

    id_item_regra: Mapped[int] = mapped_column(primary_key=True)
    nome_item: Mapped[str] = mapped_column(String, nullable=False)
    tipo_item: Mapped[str] = mapped_column(String, nullable=False)
    valor_percentual: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    ordem_aplicacao: Mapped[int] = mapped_column(nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_regra: Mapped[int] = mapped_column(
        ForeignKey("regras_calculo.id_regra"), nullable=False
    )

    regra: Mapped[RegraCalculo] = relationship(back_populates="itens")

    obrigatorio: Mapped[bool] = mapped_column(default=True, server_default="true")
