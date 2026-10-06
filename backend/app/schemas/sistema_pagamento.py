from pydantic import BaseModel, ConfigDict


class SistemaPagamentoBase(BaseModel):
    nome: str
    descricao: str | None = None
    situacao: str


class SistemaPagamentoCreate(SistemaPagamentoBase):
    model_config = ConfigDict(extra="forbid")


class SistemaPagamentoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = None
    descricao: str | None = None
    situacao: str | None = None


class SistemaPagamentoRead(SistemaPagamentoBase):
    model_config = ConfigDict(from_attributes=True)

    id_sistema: int
