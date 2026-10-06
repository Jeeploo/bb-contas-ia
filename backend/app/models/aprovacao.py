from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ordem_pagamento import OrdemPagamento
    from app.models.usuario import Usuario


class Aprovacao(Base):
    __tablename__ = "aprovacoes"

    id_aprovacao: Mapped[int] = mapped_column(primary_key=True)
    data_hora: Mapped[datetime] = mapped_column(nullable=False)
    decisao: Mapped[str] = mapped_column(String, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_ordem: Mapped[int] = mapped_column(
        ForeignKey("ordens_pagamento.id_ordem"), nullable=False
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"), nullable=False
    )

    ordem: Mapped[OrdemPagamento] = relationship(back_populates="aprovacoes")
    usuario: Mapped[Usuario] = relationship(back_populates="aprovacoes")
