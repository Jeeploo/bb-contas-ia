from pydantic import BaseModel, ConfigDict


class ConcessionariaBase(BaseModel):
    cnpj: str
    razao_social: str
    nome_fantasia: str | None = None
    tipo_servico: str


class ConcessionariaCreate(ConcessionariaBase):
    model_config = ConfigDict(extra="forbid")


class ConcessionariaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cnpj: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    tipo_servico: str | None = None
    ativo: bool | None = None


class ConcessionariaRead(ConcessionariaBase):
    model_config = ConfigDict(from_attributes=True)

    id_concessionaria: int
