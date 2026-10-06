from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import re
from typing import Protocol
import unicodedata


@dataclass(frozen=True)
class ExtractedField:
    campo_identificado: str
    valor_extraido: str
    nivel_confianca: Decimal = Decimal("95")


class FieldExtractor(Protocol):
    def extract(self, text: str) -> list[ExtractedField]: ...


class DeterministicFieldExtractor:
    """Somente linhas com rótulo explícito e valor completo reconhecido.

    Valores diferentes ou ocorrências malformadas do mesmo campo o excluem.
    Confiança 95 é uma regra fixa, não uma probabilidade de IA.
    """

    labels = {
        "codigo de barras": "codigo_barras", "linha digitavel": "codigo_barras",
        "valor total": "valor_original", "total a pagar": "valor_original",
        "data de vencimento": "data_vencimento", "vencimento": "data_vencimento",
        "consumo": "consumo", "competencia": "competencia",
    }

    def _normalize_value(self, field: str, value: str) -> str | None:
        if field == "codigo_barras":
            if not re.fullmatch(r"[0-9 .-]+", value):
                return None
            digits = re.sub(r"\D", "", value)
            return digits if len(digits) in (44, 47, 48) else None
        if field in ("valor_original", "consumo"):
            pattern = (r"(?:R\$\s*)?((?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})"
                       if field == "valor_original" else
                       r"((?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,3})?)\s*(?:kwh|m3|m³)")
            match = re.fullmatch(pattern, value, flags=re.I)
            return str(Decimal(match[1].replace(".", "").replace(",", "."))) if match else None
        if field == "data_vencimento":
            if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
                return None
            try:
                return datetime.strptime(value, "%d/%m/%Y").date().isoformat()
            except ValueError:
                return None
        if field == "competencia":
            if re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", value):
                return value[3:] + "-" + value[:2]
            if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
                return value
        return None

    def extract(self, text: str) -> list[ExtractedField]:
        candidates: dict[str, list[str | None]] = {}
        for line in text.splitlines():
            # Rótulo e valor precisam estar na mesma linha, separados por ':'.
            label, separator, value = line.partition(":")
            label = "".join(c for c in unicodedata.normalize("NFD", label.lower())
                            if not unicodedata.combining(c)).strip()
            field = self.labels.get(label)
            if separator and field:
                candidates.setdefault(field, []).append(self._normalize_value(field, value.strip()))
        return [ExtractedField(field, values[0]) for field, values in candidates.items()
                if None not in values and len(set(values)) == 1]
