from pydantic import BaseModel, ConfigDict


class UsuarioBase(BaseModel):
    matricula: str
    nome: str
    funcao: str
    situacao: str
    id_alcada: int | None = None
    id_prefixo: int | None = None


class UsuarioCreate(UsuarioBase):
    model_config = ConfigDict(extra="forbid")


class UsuarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matricula: str | None = None
    nome: str | None = None
    funcao: str | None = None
    situacao: str | None = None
    id_alcada: int | None = None
    id_prefixo: int | None = None


class UsuarioRead(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
