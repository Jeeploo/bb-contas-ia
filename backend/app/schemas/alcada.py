from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AlcadaBase(BaseModel):
    nome_nivel: str
    limite_financeiro: Decimal
    data_inicio_vigencia: date
    data_fim_vigencia: date | None = None


class AlcadaCreate(AlcadaBase):
    model_config = ConfigDict(extra="forbid")


class AlcadaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome_nivel: str | None = None
    limite_financeiro: Decimal | None = None
    data_inicio_vigencia: date | None = None
    data_fim_vigencia: date | None = None


class AlcadaRead(AlcadaBase):
    model_config = ConfigDict(from_attributes=True)

    id_alcada: int
