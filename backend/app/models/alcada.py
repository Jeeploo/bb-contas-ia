from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class Alcada(Base):
    __tablename__ = "alcadas"

    id_alcada: Mapped[int] = mapped_column(primary_key=True)
    nome_nivel: Mapped[str] = mapped_column(String, nullable=False)
    limite_financeiro: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    data_inicio_vigencia: Mapped[date] = mapped_column(nullable=False)
    data_fim_vigencia: Mapped[date | None] = mapped_column(nullable=True)

    usuarios: Mapped[list[Usuario]] = relationship(back_populates="alcada")
