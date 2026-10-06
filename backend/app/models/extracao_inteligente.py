from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.documento import Documento
    from app.models.dado_extraido import DadoExtraido


class ExtracaoInteligente(Base):
    __tablename__ = "extracoes_inteligentes"

    id_extracao: Mapped[int] = mapped_column(primary_key=True)
    data_processamento: Mapped[datetime] = mapped_column(nullable=False)
    nivel_confianca: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    situacao_validacao: Mapped[str] = mapped_column(String, nullable=False)
    id_documento: Mapped[int] = mapped_column(
        ForeignKey("documentos.id_documento"), nullable=False
    )

    documento: Mapped[Documento] = relationship(back_populates="extracoes")
    dados_extraidos: Mapped[list[DadoExtraido]] = relationship(back_populates="extracao")
