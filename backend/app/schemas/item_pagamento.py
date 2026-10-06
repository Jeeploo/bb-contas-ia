from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ItemPagamentoBase(BaseModel):
    codigo_evento: str
    descricao_evento: str | None = None
    codigo_subitem: str | None = None
    descricao_subitem: str | None = None
    valor: Decimal
    id_ordem: int


class ItemPagamentoCreate(ItemPagamentoBase):
    model_config = ConfigDict(extra="forbid")


class ItemPagamentoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo_evento: str | None = None
    descricao_evento: str | None = None
    codigo_subitem: str | None = None
    descricao_subitem: str | None = None
    valor: Decimal | None = None
    id_ordem: int | None = None


class ItemPagamentoRead(ItemPagamentoBase):
    model_config = ConfigDict(from_attributes=True)

    id_item_pagamento: int
