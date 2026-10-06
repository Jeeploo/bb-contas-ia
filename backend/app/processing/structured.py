"""Estrutura sem coordenadas; aliases pequenos e extensíveis.

Tabela de componentes: descrição | quantidade | preço unitário | valor.
Tabela tributária: tributo | base | alíquota | valor. Só valor também é aceito.
Linhas desconhecidas ou números ambíguos não são inferidos.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import re
import unicodedata
from typing import Protocol
from app.processing.fields import DeterministicFieldExtractor, ExtractedField


def normalize(text):
    text = "".join(c for c in unicodedata.normalize("NFD", text.upper()) if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


ALIASES = {
    "TUSD": ["TUSD", "Consumo-TUSD", "USO SIST. DISTR. (TUSD)"],
    "TE": ["TE", "Consumo-TE", "ENERGIA (TE)"],
    "BANDEIRA": ["bandeira", "bandeira amarela", "bandeira vermelha"],
    "ILUMINACAO_PUBLICA": ["iluminação pública", "contribuição iluminação pública", "CIP"],
    "ICMS": ["ICMS"], "PIS": ["PIS"], "COFINS": ["COFINS"],
    "DESCONTO": ["desconto", "descontos"],
}


@dataclass(frozen=True)
class ExtractedItem:
    descricao_original: str
    tipo_normalizado: str
    valor: Decimal
    categoria: str = "componente"
    quantidade: Decimal | None = None
    unidade: str | None = None
    valor_unitario: Decimal | None = None
    base_calculo: Decimal | None = None
    aliquota: Decimal | None = None
    nivel_confianca: Decimal = Decimal("90")


@dataclass(frozen=True)
class StructuredExtraction:
    campos: list[ExtractedField] = field(default_factory=list)
    itens: list[ExtractedItem] = field(default_factory=list)


class StructuredDocumentExtractor(Protocol):
    def extract(self, text: str, context: dict) -> StructuredExtraction: ...


def number(value):
    value = re.sub(r"(?i)R\$|kwh|m³|m3|%", "", value).strip()
    if not re.fullmatch(r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?|\d+\.\d+", value):
        return None
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return Decimal(value)


class DeterministicStructuredExtractor:
    def __init__(self, aliases=None):
        self.aliases = {normalize(alias): kind for kind, names in (aliases or ALIASES).items() for alias in names}
        self.fields = DeterministicFieldExtractor()

    def extract(self, text, context=None):
        # Rótulo em linha própria ou separado por ':' / '|' / dois espaços.
        lines = text.splitlines()
        canonical = []
        items = []
        for index, raw in enumerate(lines):
            pieces = [p.strip() for p in re.split(r"\s*[|:]\s*|\s{2,}", raw.strip()) if p.strip()]
            if not pieces:
                continue
            label = normalize(pieces[0]).lower()
            if len(pieces) == 1 and label in self.fields.labels and index + 1 < len(lines):
                canonical.append(pieces[0] + ": " + lines[index + 1].strip())
            elif label in self.fields.labels and len(pieces) == 2:
                canonical.append(pieces[0] + ": " + pieces[1])
            else:
                # Também aceita descrição seguida por valor, sem separador visual fixo.
                if len(pieces) == 1:
                    match = re.fullmatch(r"(.+?)\s+((?:R\$\s*)?\d[\d.,]*)", pieces[0])
                    if match:
                        pieces = [match[1], match[2]]
                kind = self.aliases.get(normalize(pieces[0]))
                if kind is None or len(pieces) not in (2, 4):
                    continue
                values = [number(p) for p in pieces[1:]]
                if any(v is None for v in values):
                    continue
                tax = kind in ("ICMS", "PIS", "COFINS")
                kwargs = {}
                if len(values) == 3:
                    if tax:
                        kwargs = dict(base_calculo=values[0], aliquota=values[1])
                    else:
                        kwargs = dict(quantidade=values[0], valor_unitario=values[1],
                                      unidade="kWh" if "kwh" in pieces[1].lower() else None)
                items.append(ExtractedItem(descricao_original=raw.strip(), tipo_normalizado=kind,
                    categoria="tributo" if tax else "componente", valor=values[-1], **kwargs))
        return StructuredExtraction(self.fields.extract("\n".join(canonical)), items)
