from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.localidade import Localidade


class Prefixo(Base):
    __tablename__ = "prefixos"

    id_prefixo: Mapped[int] = mapped_column(primary_key=True)
    codigo_prefixo: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    tipo_prefixo: Mapped[str] = mapped_column(String, nullable=False)
    situacao: Mapped[str] = mapped_column(String, nullable=False)
    id_localidade: Mapped[int] = mapped_column(
        ForeignKey("localidades.id_localidade"), nullable=False
    )

    localidade: Mapped[Localidade] = relationship(back_populates="prefixos")
