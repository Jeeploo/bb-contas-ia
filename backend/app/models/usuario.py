from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.usuario_prefixo import UsuarioPrefixo
    from app.models.alcada import Alcada
    from app.models.aprovacao import Aprovacao
    from app.models.ordem_pagamento import OrdemPagamento
    from app.models.prefixo import Prefixo


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    funcao: Mapped[str] = mapped_column(String, nullable=False)
    situacao: Mapped[str] = mapped_column(String, nullable=False)
    id_alcada: Mapped[int | None] = mapped_column(
        ForeignKey("alcadas.id_alcada"), nullable=True
    )
    id_prefixo: Mapped[int | None] = mapped_column(
        ForeignKey("prefixos.id_prefixo"), nullable=True
    )

    vinculos_prefixos: Mapped[list["UsuarioPrefixo"]] = relationship(
        "UsuarioPrefixo", back_populates="usuario", cascade="all, delete-orphan")

    alcada: Mapped[Alcada | None] = relationship(back_populates="usuarios")
    prefixo: Mapped[Prefixo | None] = relationship(back_populates="usuarios")
    ordens_criadas: Mapped[list[OrdemPagamento]] = relationship(
        back_populates="usuario_criador"
    )
    aprovacoes: Mapped[list[Aprovacao]] = relationship(back_populates="usuario")
