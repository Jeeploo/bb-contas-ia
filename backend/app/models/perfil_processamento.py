from datetime import date
from sqlalchemy import ForeignKey, JSON, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class PerfilProcessamento(Base):
    __tablename__ = "perfis_processamento"
    __table_args__ = (CheckConstraint("data_fim_vigencia IS NULL OR data_fim_vigencia >= data_inicio_vigencia", name="ck_perfil_vigencia"),)

    id_perfil: Mapped[int] = mapped_column(primary_key=True)
    id_prefixo: Mapped[int] = mapped_column(ForeignKey("prefixos.id_prefixo"), index=True)
    tipo_servico: Mapped[str] = mapped_column(String)
    estrategia: Mapped[str] = mapped_column(String)
    id_regra: Mapped[int] = mapped_column(ForeignKey("regras_calculo.id_regra"))
    id_concessionaria: Mapped[int | None] = mapped_column(ForeignKey("concessionarias.id_concessionaria"), nullable=True)
    situacao: Mapped[str] = mapped_column(String)
    data_inicio_vigencia: Mapped[date] = mapped_column()
    data_fim_vigencia: Mapped[date | None] = mapped_column(nullable=True)
    parametros: Mapped[dict] = mapped_column(JSON, default=dict)
