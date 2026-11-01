"""Normalização conservadora. O payload original é preservado separadamente."""
from datetime import datetime
from decimal import Decimal
import re
from pydantic import ValidationError
from app.schemas.leitura_documental import LeituraDocumental
from app.document_ai.base import DocumentAIError


NUMERICOS = {name for name, spec in LeituraDocumental.model_fields.items() if 'Decimal' in str(spec.annotation)}


def normalizar_leitura(original: dict) -> LeituraDocumental:
    try:
        if not isinstance(original, dict) or set(original) - set(LeituraDocumental.model_fields):
            raise ValueError('Formato incompatível')
        data = {k: (' '.join(v.split()) if isinstance(v, str) else v) for k, v in original.items()}
        data = {k: (None if v == '' else v) for k, v in data.items()}
        if data.get('tipo_documento') not in (None, 'CONTA_ENERGIA', 'CONTA_AGUA', 'OUTRO'):
            raise ValueError('Tipo fora das categorias MVP')
        if data.get('uf'):
            data['uf'] = data['uf'].upper()
        for name in NUMERICOS:
            value = data.get(name)
            if isinstance(value, bool):
                raise ValueError('Booleano não é um valor')
            if isinstance(value, str):
                value = re.sub(r'^R\$\s*', '', value).strip()
                if ',' in value:
                    if not re.fullmatch(r'(?:\d{1,3}(?:\.\d{3})+|\d+),\d+', value):
                        raise ValueError('Número ambíguo')
                    value = value.replace('.', '').replace(',', '.')
                elif not re.fullmatch(r'\d+(?:\.\d+)?', value):
                    raise ValueError('Número inválido')
                data[name] = Decimal(value)
        for name in ('data_emissao', 'data_vencimento'):
            value = data.get(name)
            if isinstance(value, str) and re.fullmatch(r'\d{2}/\d{2}/\d{4}', value):
                data[name] = datetime.strptime(value, '%d/%m/%Y').date()
        if data.get('competencia') and re.fullmatch(r'\d{2}/\d{4}', data['competencia']):
            data['competencia'] = data['competencia'][3:]+'-'+data['competencia'][:2]
        if data.get('unidade_consumo'):
            unit = data['unidade_consumo'].lower().replace('³', '3')
            if unit in ('kwh', 'm3'):
                data['unidade_consumo'] = 'kWh' if unit == 'kwh' else 'm3'
        if data.get('codigo_barras'):
            if not re.fullmatch(r'[0-9 .-]+', data['codigo_barras']):
                raise ValueError('Código de barras inválido')
            data['codigo_barras'] = re.sub(r'\D', '', data['codigo_barras'])
            if len(data['codigo_barras']) not in (44, 47, 48):
                raise ValueError('Código de barras incompleto')
        return LeituraDocumental.model_validate(data)
    except (ValueError, TypeError, AttributeError, ArithmeticError, ValidationError):
        raise DocumentAIError('resposta_invalida') from None
