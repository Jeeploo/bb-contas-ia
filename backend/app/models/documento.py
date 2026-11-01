from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, JSON, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conta_consumo import ContaConsumo
    from app.models.extracao_inteligente import ExtracaoInteligente


class Documento(Base):
    __tablename__ = "documentos"

    historico_leitura_ia: Mapped[list] = mapped_column(JSON, default=list, server_default=text("'[]'"))

    id_documento: Mapped[int] = mapped_column(primary_key=True)
    tipo_documento: Mapped[str] = mapped_column(String, nullable=False)
    formato: Mapped[str] = mapped_column(String, nullable=False)
    data_recebimento: Mapped[datetime] = mapped_column(nullable=False)
    origem: Mapped[str] = mapped_column(String, nullable=False)
    caminho_arquivo: Mapped[str] = mapped_column(String, nullable=False)
    id_conta: Mapped[int] = mapped_column(
        ForeignKey("contas_consumo.id_conta"), nullable=False
    )

    conta: Mapped[ContaConsumo] = relationship(back_populates="documentos")
    extracoes: Mapped[list[ExtracaoInteligente]] = relationship(back_populates="documento")
