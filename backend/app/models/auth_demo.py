"""Credenciais locais e sessões opacas; nunca serializadas pelas APIs cadastrais."""
from datetime import datetime
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class CredencialDemo(Base):
    __tablename__ = 'credenciais_demo'
    id_usuario: Mapped[int] = mapped_column(ForeignKey('usuarios.id_usuario'), primary_key=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    fator_hash: Mapped[str] = mapped_column(String, nullable=False)


class SessaoDemo(Base):
    __tablename__ = 'sessoes_demo'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey('usuarios.id_usuario'), nullable=False, index=True)
    id_prefixo: Mapped[int | None] = mapped_column(ForeignKey('prefixos.id_prefixo'), nullable=True)
    expira_em: Mapped[datetime] = mapped_column(nullable=False)
