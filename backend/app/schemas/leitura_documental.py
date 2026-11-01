"""Contrato independente do mecanismo de leitura. Nenhuma decisão de autorização."""
from datetime import date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResultadoDocumental(str, Enum):
    VALIDO = "VALIDO"
    DOCUMENTO_NAO_SUPORTADO = "DOCUMENTO_NAO_SUPORTADO"
    REGIAO_NAO_SUPORTADA = "REGIAO_NAO_SUPORTADA"
    DIVERGENCIA_PREFIXO = "DIVERGENCIA_PREFIXO"
    EVIDENCIA_INSUFICIENTE = "EVIDENCIA_INSUFICIENTE"


class LeituraDocumental(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    tipo_documento: str | None = None
    concessionaria: str | None = None
    numero_documento: str | None = None
    unidade_consumidora: str | None = None
    competencia: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    data_emissao: date | None = None
    data_vencimento: date | None = None
    valor_total: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    codigo_barras: str | None = None
    endereco_unidade: str | None = None
    municipio: str | None = None
    uf: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$")
    consumo: Decimal | None = Field(default=None, ge=0)
    unidade_consumo: str | None = None
    consumo_kwh: Decimal | None = Field(default=None, ge=0)
    consumo_m3: Decimal | None = Field(default=None, ge=0)
    leitura_anterior: Decimal | None = Field(default=None, ge=0)
    leitura_atual: Decimal | None = Field(default=None, ge=0)
    periodo_leitura: str | None = None
    demanda: Decimal | None = Field(default=None, ge=0)
    tusd: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    te: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    bandeira_tarifaria: str | None = None
    valor_bandeira_tarifaria: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    iluminacao_publica: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    icms: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    pis: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    cofins: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    tarifa_agua: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    tarifa_esgoto: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    percentual_esgoto: Decimal | None = Field(default=None, ge=0, le=100)
    servicos_adicionais: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    descontos: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    multas: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    juros: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    outros_encargos: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def consumo_consistente(self):
        if self.consumo_kwh is not None and self.consumo_m3 is not None:
            raise ValueError("Consumo não pode ser simultaneamente de energia e água")
        tipo = (self.tipo_documento or "").upper()
        if tipo in {"ENERGIA", "CONTA_ENERGIA"} and self.consumo_m3 is not None:
            raise ValueError("Conta de energia não pode informar consumo_m3")
        if tipo in {"AGUA", "CONTA_AGUA", "AGUA_SANEAMENTO"} and self.consumo_kwh is not None:
            raise ValueError("Conta de água não pode informar consumo_kwh")
        specific = self.consumo_kwh if self.consumo_kwh is not None else self.consumo_m3
        unit = "kWh" if self.consumo_kwh is not None else "m3"
        if specific is not None:
            if self.consumo is not None and self.consumo != specific:
                raise ValueError("Consumos inconsistentes")
            if self.unidade_consumo and self.unidade_consumo.lower().replace("³", "3") != unit.lower():
                raise ValueError("Unidade de consumo inconsistente")
        return self

    def dados_canonicos(self):
        data = self.model_dump(exclude_none=True)
        kwh, m3 = data.pop("consumo_kwh", None), data.pop("consumo_m3", None)
        if kwh is not None or m3 is not None:
            data["consumo"] = kwh if kwh is not None else m3
            data["unidade_consumo"] = "kWh" if kwh is not None else "m3"
        if "valor_total" in data:
            data["valor_original"] = data.pop("valor_total")
        return data


class ContextoDocumental(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_usuario: int = Field(gt=0)
    id_prefixo: int | None = Field(default=None, gt=0)
