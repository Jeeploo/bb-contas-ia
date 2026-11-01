from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, JSON, CheckConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.documento import Documento
    from app.models.dado_extraido import DadoExtraido
    from app.models.item_extraido import ItemExtraido


class ExtracaoInteligente(Base):
    __tablename__ = "extracoes_inteligentes"

    __table_args__ = (CheckConstraint("resultado_validacao_documental IN ('VALIDO', 'DOCUMENTO_NAO_SUPORTADO', 'REGIAO_NAO_SUPORTADA', 'DIVERGENCIA_PREFIXO', 'EVIDENCIA_INSUFICIENTE')", name="ck_resultado_documental"),)
    resultado_validacao_documental: Mapped[str] = mapped_column(String, default="EVIDENCIA_INSUFICIENTE", server_default="EVIDENCIA_INSUFICIENTE")
    motivo_validacao_documental: Mapped[str | None] = mapped_column(String, nullable=True)
    evidencias_validacao_documental: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    historico_validacao_documental: Mapped[list] = mapped_column(JSON, default=list, server_default=text("'[]'"))
    id_usuario_contexto: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=True)
    id_prefixo_contexto: Mapped[int | None] = mapped_column(ForeignKey("prefixos.id_prefixo"), nullable=True)

    metadados_ia: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resposta_original_ia: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    id_extracao: Mapped[int] = mapped_column(primary_key=True)
    data_processamento: Mapped[datetime] = mapped_column(nullable=False)
    nivel_confianca: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    situacao_validacao: Mapped[str] = mapped_column(String, nullable=False)
    id_documento: Mapped[int] = mapped_column(
        ForeignKey("documentos.id_documento"), nullable=False
    )

    documento: Mapped[Documento] = relationship(back_populates="extracoes")
    dados_extraidos: Mapped[list[DadoExtraido]] = relationship(back_populates="extracao")

    itens_extraidos: Mapped[list[ItemExtraido]] = relationship("ItemExtraido", back_populates="extracao")
