from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrdemPagamentoBase(BaseModel):
    data_criacao: datetime
    data_prevista_pagamento: date
    valor_total: Decimal
    situacao: str
    id_calculo: int
    id_sistema: int
    id_usuario_criador: int


class OrdemPagamentoCreate(OrdemPagamentoBase):
    id_usuario_criador: int | None = None
    model_config = ConfigDict(extra="forbid")


class OrdemPagamentoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_criacao: datetime | None = None
    data_prevista_pagamento: date | None = None
    valor_total: Decimal | None = None
    situacao: str | None = None
    id_calculo: int | None = None
    id_sistema: int | None = None
    id_usuario_criador: int | None = None


class OrdemPagamentoRead(OrdemPagamentoBase):
    model_config = ConfigDict(from_attributes=True)

    id_ordem: int
