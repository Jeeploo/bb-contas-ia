from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ItemRegraBase(BaseModel):
    obrigatorio: bool = True
    nome_item: str
    tipo_item: str
    valor_percentual: Decimal | None = None
    ordem_aplicacao: int
    descricao: str | None = None
    id_regra: int


class ItemRegraCreate(ItemRegraBase):
    model_config = ConfigDict(extra="forbid")


class ItemRegraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obrigatorio: bool | None = None
    nome_item: str | None = None
    tipo_item: str | None = None
    valor_percentual: Decimal | None = None
    ordem_aplicacao: int | None = None
    descricao: str | None = None
    id_regra: int | None = None


class ItemRegraRead(ItemRegraBase):
    model_config = ConfigDict(from_attributes=True)

    id_item_regra: int
