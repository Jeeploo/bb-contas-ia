from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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
