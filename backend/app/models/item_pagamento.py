from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ordem_pagamento import OrdemPagamento


class ItemPagamento(Base):
    __tablename__ = "itens_pagamento"

    id_item_pagamento: Mapped[int] = mapped_column(primary_key=True)
    codigo_evento: Mapped[str] = mapped_column(String, nullable=False)
    descricao_evento: Mapped[str | None] = mapped_column(String, nullable=True)
    codigo_subitem: Mapped[str | None] = mapped_column(String, nullable=True)
    descricao_subitem: Mapped[str | None] = mapped_column(String, nullable=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    id_ordem: Mapped[int] = mapped_column(
        ForeignKey("ordens_pagamento.id_ordem"), nullable=False
    )

    ordem: Mapped[OrdemPagamento] = relationship(back_populates="itens")
