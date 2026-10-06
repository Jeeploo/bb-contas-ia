from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CalculoBase(BaseModel):
    data_calculo: datetime
    valor_inicial: Decimal
    valor_calculado: Decimal
    situacao: str
    id_conta: int
    id_regra: int


class CalculoCreate(CalculoBase):
    model_config = ConfigDict(extra="forbid")


class CalculoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_calculo: datetime | None = None
    valor_inicial: Decimal | None = None
    valor_calculado: Decimal | None = None
    situacao: str | None = None
    id_conta: int | None = None
    id_regra: int | None = None


class CalculoRead(CalculoBase):
    model_config = ConfigDict(from_attributes=True)

    memoria_calculo: dict | None = None
    id_calculo: int
