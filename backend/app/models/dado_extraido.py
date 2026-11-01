from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.extracao_inteligente import ExtracaoInteligente


class DadoExtraido(Base):
    __tablename__ = "dados_extraidos"

    id_dado_extraido: Mapped[int] = mapped_column(primary_key=True)
    campo_identificado: Mapped[str] = mapped_column(String, nullable=False)
    valor_normalizado: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_extraido: Mapped[str | None] = mapped_column(Text, nullable=True)
    nivel_confianca: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    situacao_validacao: Mapped[str] = mapped_column(String, nullable=False)
    valor_validado: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_extracao: Mapped[int] = mapped_column(
        ForeignKey("extracoes_inteligentes.id_extracao"), nullable=False
    )

    extracao: Mapped[ExtracaoInteligente] = relationship(back_populates="dados_extraidos")
