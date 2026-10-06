from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ContaConsumoBase(BaseModel):
    numero_conta: str | None = None
    competencia: str
    data_emissao: date | None = None
    data_vencimento: date
    valor_original: Decimal
    codigo_barras: str | None = None
    consumo: Decimal | None = None
    unidade_consumo: str | None = None
    categoria: str
    situacao: str
    id_prefixo: int
    id_concessionaria: int


class ContaConsumoCreate(ContaConsumoBase):
    model_config = ConfigDict(extra="forbid")


class ContaConsumoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero_conta: str | None = None
    competencia: str | None = None
    data_emissao: date | None = None
    data_vencimento: date | None = None
    valor_original: Decimal | None = None
    codigo_barras: str | None = None
    consumo: Decimal | None = None
    unidade_consumo: str | None = None
    categoria: str | None = None
    situacao: str | None = None
    id_prefixo: int | None = None
    id_concessionaria: int | None = None


class ContaConsumoRead(ContaConsumoBase):
    model_config = ConfigDict(from_attributes=True)

    id_conta: int
