from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ConcessionariaAlias(Base):
    __tablename__ = "concessionaria_aliases"
    __table_args__ = (UniqueConstraint("alias_normalizado", "id_concessionaria", name="uq_alias_concessionaria"),)
    id_alias: Mapped[int] = mapped_column(primary_key=True)
    id_concessionaria: Mapped[int] = mapped_column(ForeignKey("concessionarias.id_concessionaria"), nullable=False)
    alias: Mapped[str] = mapped_column(String, nullable=False)
    alias_normalizado: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
