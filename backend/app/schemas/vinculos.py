from pydantic import BaseModel, ConfigDict, Field


class UsuarioPrefixoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_prefixo: int = Field(gt=0)
    ativo: bool = True
    principal: bool = False


class UsuarioPrefixosDefinicao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vinculos: list[UsuarioPrefixoEntrada]


class UnidadeConsumidoraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id_prefixo: int = Field(gt=0)
    id_concessionaria: int = Field(gt=0)
    unidade_consumidora: str = Field(min_length=1)
    ativo: bool = True
    endereco_referencia: str | None = None


class UnidadeConsumidoraRead(UnidadeConsumidoraCreate):
    model_config = ConfigDict(from_attributes=True)
    id_unidade_consumidora: int


class UnidadeConsumidoraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ativo: bool | None = None
    endereco_referencia: str | None = None
