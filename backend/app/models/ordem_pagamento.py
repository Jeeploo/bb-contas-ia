from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.aprovacao import Aprovacao
    from app.models.calculo import Calculo
    from app.models.item_pagamento import ItemPagamento
    from app.models.sistema_pagamento import SistemaPagamento
    from app.models.usuario import Usuario


class OrdemPagamento(Base):
    __tablename__ = "ordens_pagamento"

    id_ordem: Mapped[int] = mapped_column(primary_key=True)
    data_criacao: Mapped[datetime] = mapped_column(nullable=False)
    data_prevista_pagamento: Mapped[date] = mapped_column(nullable=False)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    situacao: Mapped[str] = mapped_column(String, nullable=False)
    id_calculo: Mapped[int] = mapped_column(
        ForeignKey("calculos.id_calculo"), nullable=False
    )
    id_sistema: Mapped[int] = mapped_column(
        ForeignKey("sistemas_pagamento.id_sistema"), nullable=False
    )
    id_usuario_criador: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"), nullable=False
    )

    calculo: Mapped[Calculo] = relationship(back_populates="ordens")
    sistema: Mapped[SistemaPagamento] = relationship(back_populates="ordens")
    usuario_criador: Mapped[Usuario] = relationship(back_populates="ordens_criadas")
    itens: Mapped[list[ItemPagamento]] = relationship(back_populates="ordem")
    aprovacoes: Mapped[list[Aprovacao]] = relationship(back_populates="ordem")
