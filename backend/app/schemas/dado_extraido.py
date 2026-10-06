from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DadoExtraidoBase(BaseModel):
    campo_identificado: str
    valor_extraido: str | None = None
    nivel_confianca: Decimal | None = None
    situacao_validacao: str
    valor_validado: str | None = None
    id_extracao: int


class DadoExtraidoCreate(DadoExtraidoBase):
    model_config = ConfigDict(extra="forbid")


class DadoExtraidoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campo_identificado: str | None = None
    valor_extraido: str | None = None
    nivel_confianca: Decimal | None = None
    situacao_validacao: str | None = None
    valor_validado: str | None = None
    id_extracao: int | None = None


class DadoExtraidoRead(DadoExtraidoBase):
    model_config = ConfigDict(from_attributes=True)

    id_dado_extraido: int
