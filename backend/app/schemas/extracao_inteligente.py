from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.leitura_documental import ResultadoDocumental


class ExtracaoInteligenteBase(BaseModel):
    data_processamento: datetime
    nivel_confianca: Decimal | None = None
    situacao_validacao: str
    id_documento: int


class ExtracaoInteligenteCreate(ExtracaoInteligenteBase):
    model_config = ConfigDict(extra="forbid")


class ExtracaoInteligenteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_processamento: datetime | None = None
    nivel_confianca: Decimal | None = None
    situacao_validacao: str | None = None
    id_documento: int | None = None


class ExtracaoInteligenteRead(ExtracaoInteligenteBase):
    model_config = ConfigDict(from_attributes=True)

    id_extracao: int
    resultado_validacao_documental: ResultadoDocumental = ResultadoDocumental.EVIDENCIA_INSUFICIENTE
    motivo_validacao_documental: str | None = None
    evidencias_validacao_documental: dict = Field(default_factory=dict)
    historico_validacao_documental: list[dict] = Field(default_factory=list)
    id_usuario_contexto: int | None = None
    id_prefixo_contexto: int | None = None

    pendencias: list[dict] = Field(default_factory=list)
    permite_envio_validacao: bool = False
    bloqueia_calculo: bool = True

    @model_validator(mode="before")
    @classmethod
    def politica(cls, value):
        if not isinstance(value, dict):
            from app.services.validacao_documental import politica_revisao
            return {**{name: getattr(value, name) for name in cls.model_fields
                       if hasattr(value, name)}, **politica_revisao(value)}
        return value
