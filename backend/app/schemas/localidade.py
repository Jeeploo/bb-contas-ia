from pydantic import BaseModel, ConfigDict, Field


class LocalidadeBase(BaseModel):
    codigo_localidade: str
    estado: str = Field(max_length=2)
    municipio: str
    regiao: str | None = None


class LocalidadeCreate(LocalidadeBase):
    model_config = ConfigDict(extra="forbid")


class LocalidadeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo_localidade: str | None = None
    estado: str | None = Field(default=None, max_length=2)
    municipio: str | None = None
    regiao: str | None = None


class LocalidadeRead(LocalidadeBase):
    model_config = ConfigDict(from_attributes=True)

    id_localidade: int
