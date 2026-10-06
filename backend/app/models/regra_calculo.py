from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.calculo import Calculo
    from app.models.item_regra import ItemRegra


class RegraCalculo(Base):
    __tablename__ = "regras_calculo"

    id_regra: Mapped[int] = mapped_column(primary_key=True)
    nome_regra: Mapped[str] = mapped_column(String, nullable=False)
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    versao: Mapped[str] = mapped_column(String, nullable=False)
    data_inicio_vigencia: Mapped[date] = mapped_column(nullable=False)
    data_fim_vigencia: Mapped[date | None] = mapped_column(nullable=True)
    situacao: Mapped[str] = mapped_column(String, nullable=False)

    itens: Mapped[list[ItemRegra]] = relationship(back_populates="regra")
    calculos: Mapped[list[Calculo]] = relationship(back_populates="regra")
