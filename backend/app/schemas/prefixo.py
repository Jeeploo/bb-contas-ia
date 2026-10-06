from pydantic import BaseModel, ConfigDict


class PrefixoBase(BaseModel):
    codigo_prefixo: str
    nome: str
    tipo_prefixo: str
    situacao: str
    id_localidade: int


class PrefixoCreate(PrefixoBase):
    model_config = ConfigDict(extra="forbid")


class PrefixoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo_prefixo: str | None = None
    nome: str | None = None
    tipo_prefixo: str | None = None
    situacao: str | None = None
    id_localidade: int | None = None


class PrefixoRead(PrefixoBase):
    model_config = ConfigDict(from_attributes=True)

    id_prefixo: int
