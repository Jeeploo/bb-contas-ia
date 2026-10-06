from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.calculation.strategies import validate_parameters


class PerfilProcessamentoBase(BaseModel):
    id_prefixo: int
    tipo_servico: str = Field(min_length=1)
    estrategia: Literal["VALOR_INTEGRAL", "COEFICIENTE", "COMPOSICAO_DETALHADA"]
    id_regra: int
    id_concessionaria: int | None = None
    situacao: str
    data_inicio_vigencia: date
    data_fim_vigencia: date | None = None
    parametros: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_config(self):
        if self.data_fim_vigencia and self.data_fim_vigencia < self.data_inicio_vigencia:
            raise ValueError("Vigência final anterior à inicial")
        validate_parameters(self.estrategia, self.parametros)
        return self


class PerfilProcessamentoCreate(PerfilProcessamentoBase):
    model_config = ConfigDict(extra="forbid")


class PerfilProcessamentoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_prefixo: int | None = None
    tipo_servico: str | None = None
    estrategia: str | None = None
    id_regra: int | None = None
    id_concessionaria: int | None = None
    situacao: str | None = None
    data_inicio_vigencia: date | None = None
    data_fim_vigencia: date | None = None
    parametros: dict | None = None


class PerfilProcessamentoRead(PerfilProcessamentoBase):
    model_config = ConfigDict(from_attributes=True)
    id_perfil: int
