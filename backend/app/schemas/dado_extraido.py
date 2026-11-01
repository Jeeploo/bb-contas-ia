from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class DadoExtraidoValidacao(BaseModel):
    """Omitir valor_validado confirma o original; null não é uma correção."""
    model_config = ConfigDict(extra="forbid")

    valor_validado: str | None = Field(default=None, min_length=1)

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null(cls, data):
        if isinstance(data, dict) and "valor_validado" in data and data["valor_validado"] is None:
            raise ValueError("Informe um valor válido ou omita o campo para confirmar o original")
        return data


class DadoExtraidoPatch(BaseModel):
    """Somente invalidação da revisão. Correções usam /validacao."""
    model_config = ConfigDict(extra="forbid")
    situacao_validacao: str = Field(default="pendente", pattern="^pendente$")
