from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ItemExtraidoBase(BaseModel):
    id_extracao: int
    categoria: str
    descricao_original: str
    tipo_normalizado: str
    quantidade: Decimal | None = None
    unidade: str | None = None
    valor_unitario: Decimal | None = None
    valor: Decimal
    base_calculo: Decimal | None = None
    aliquota: Decimal | None = None
    nivel_confianca: Decimal | None = Field(default=None, ge=0, le=100)
    valor_validado: Decimal | None = None
    situacao_validacao: str = "pendente"


class ItemExtraidoCreate(ItemExtraidoBase):
    model_config = ConfigDict(extra="forbid")


class ItemExtraidoValidacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valor_validado: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @model_validator(mode="before")
    @classmethod
    def reject_null(cls, data):
        if isinstance(data, dict) and "valor_validado" in data and data["valor_validado"] is None:
            raise ValueError("Omita o valor para confirmar o original")
        return data


class ItemExtraidoRead(ItemExtraidoBase):
    model_config = ConfigDict(from_attributes=True)
    id_item_extraido: int
