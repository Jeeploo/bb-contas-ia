from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.conta_consumo import ContaConsumo


class Concessionaria(Base):
    __tablename__ = "concessionarias"

    id_concessionaria: Mapped[int] = mapped_column(primary_key=True)
    cnpj: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    razao_social: Mapped[str] = mapped_column(String, nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo_servico: Mapped[str] = mapped_column(String, nullable=False)

    contas: Mapped[list[ContaConsumo]] = relationship(back_populates="concessionaria")
