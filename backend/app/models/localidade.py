from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.prefixo import Prefixo


class Localidade(Base):
    __tablename__ = "localidades"

    id_localidade: Mapped[int] = mapped_column(primary_key=True)
    codigo_localidade: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    municipio: Mapped[str] = mapped_column(String, nullable=False)
    regiao: Mapped[str | None] = mapped_column(String, nullable=True)

    prefixos: Mapped[list[Prefixo]] = relationship(back_populates="localidade")
