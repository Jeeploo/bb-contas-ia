from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ordem_pagamento import OrdemPagamento


class SistemaPagamento(Base):
    __tablename__ = "sistemas_pagamento"

    id_sistema: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    situacao: Mapped[str] = mapped_column(String, nullable=False)

    ordens: Mapped[list[OrdemPagamento]] = relationship(back_populates="sistema")
