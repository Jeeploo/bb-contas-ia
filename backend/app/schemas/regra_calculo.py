from datetime import date

from pydantic import BaseModel, ConfigDict


class RegraCalculoBase(BaseModel):
    nome_regra: str
    categoria: str
    versao: str
    data_inicio_vigencia: date
    data_fim_vigencia: date | None = None
    situacao: str


class RegraCalculoCreate(RegraCalculoBase):
    model_config = ConfigDict(extra="forbid")


class RegraCalculoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome_regra: str | None = None
    categoria: str | None = None
    versao: str | None = None
    data_inicio_vigencia: date | None = None
    data_fim_vigencia: date | None = None
    situacao: str | None = None


class RegraCalculoRead(RegraCalculoBase):
    model_config = ConfigDict(from_attributes=True)

    id_regra: int
