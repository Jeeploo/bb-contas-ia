from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
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
