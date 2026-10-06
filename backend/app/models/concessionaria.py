from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Concessionaria(Base):
    __tablename__ = "concessionarias"

    id_concessionaria: Mapped[int] = mapped_column(primary_key=True)
    cnpj: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    razao_social: Mapped[str] = mapped_column(String, nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo_servico: Mapped[str] = mapped_column(String, nullable=False)
