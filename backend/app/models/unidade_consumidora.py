from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.prefixo import Prefixo
    from app.models.concessionaria import Concessionaria
from app.models.base import Base


class UnidadeConsumidora(Base):
    __tablename__ = "unidades_consumidoras"
    __table_args__ = (
        UniqueConstraint("id_concessionaria", "unidade_consumidora", name="uq_concessionaria_unidade"),
        CheckConstraint("length(trim(unidade_consumidora)) > 0", name="ck_unidade_nao_vazia"),
    )
    id_unidade_consumidora: Mapped[int] = mapped_column(primary_key=True)
    id_prefixo: Mapped[int] = mapped_column(ForeignKey("prefixos.id_prefixo"), index=True)
    id_concessionaria: Mapped[int] = mapped_column(ForeignKey("concessionarias.id_concessionaria"))
    unidade_consumidora: Mapped[str] = mapped_column(String)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    endereco_referencia: Mapped[str | None] = mapped_column(String, nullable=True)

    prefixo: Mapped["Prefixo"] = relationship()
    concessionaria: Mapped["Concessionaria"] = relationship()
