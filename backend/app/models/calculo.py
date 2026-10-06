from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conta_consumo import ContaConsumo
    from app.models.regra_calculo import RegraCalculo


class Calculo(Base):
    __tablename__ = "calculos"

    id_calculo: Mapped[int] = mapped_column(primary_key=True)
    data_calculo: Mapped[datetime] = mapped_column(nullable=False)
    valor_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    valor_calculado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    situacao: Mapped[str] = mapped_column(String, nullable=False)
    id_conta: Mapped[int] = mapped_column(
        ForeignKey("contas_consumo.id_conta"), nullable=False
    )
    id_regra: Mapped[int] = mapped_column(
        ForeignKey("regras_calculo.id_regra"), nullable=False
    )

    conta: Mapped[ContaConsumo] = relationship(back_populates="calculos")
    regra: Mapped[RegraCalculo] = relationship(back_populates="calculos")
