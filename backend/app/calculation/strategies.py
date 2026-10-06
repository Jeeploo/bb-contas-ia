"""Aritmética Decimal, independente de HTTP, OCR e persistência."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Protocol
from app.services.exceptions import CalculationError


def decimal_value(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise CalculationError("Valor decimal inválido") from None
    if not number.is_finite():
        raise CalculationError("Valor decimal deve ser finito")
    return number


def validate_parameters(strategy, parameters):
    if strategy not in STRATEGIES:
        raise CalculationError("Estratégia de cálculo desconhecida")
    if strategy == "COEFICIENTE":
        if "coeficiente" not in parameters:
            raise CalculationError("Coeficiente ausente na configuração")
        if decimal_value(parameters["coeficiente"]) <= 0:
            raise CalculationError("Coeficiente deve ser maior que zero")
    if parameters.get("arredondamento", "ROUND_HALF_UP") != "ROUND_HALF_UP":
        raise CalculationError("Arredondamento suportado: ROUND_HALF_UP em centavos")


@dataclass(frozen=True)
class Component:
    id: int
    tipo: str
    valor: Decimal | None
    validado: bool


class CalculationStrategy(Protocol):
    def execute(self, base: Decimal, parameters: dict, components: list[Component], rules: list[dict]) -> dict: ...


class IntegralValueStrategy:
    def execute(self, base, parameters, components, rules):
        return memory("VALOR_INTEGRAL", base, base, parameters, [], components)


class CoefficientStrategy:
    def execute(self, base, parameters, components, rules):
        validate_parameters("COEFICIENTE", parameters)
        with localcontext() as ctx:
            ctx.prec = 40
            result = base / decimal_value(parameters["coeficiente"])
        return memory("COEFICIENTE", base, result, parameters, [], components)


class DetailedCompositionStrategy:
    def execute(self, base, parameters, components, rules):
        if not rules:
            raise CalculationError("Composição detalhada sem itens configurados na regra")
        considered = []
        used = set()
        total = Decimal(0)
        for rule in rules:
            operation = rule["operacao"]
            if operation not in ("SOMAR", "DESCONTO"):
                raise CalculationError("Operação de composição desconhecida")
            kind = rule["tipo"].upper()
            if kind in used:
                raise CalculationError("Componente duplicado na configuração da regra")
            used.add(kind)
            matches = [c for c in components if c.tipo == kind]
            if not matches and rule.get("obrigatorio", True):
                raise CalculationError(f"Componente obrigatório ausente: {kind}")
            for c in matches:
                if not c.validado or c.valor is None:
                    raise CalculationError(f"Componente não validado: {kind}")
                value = decimal_value(c.valor)
                if value < 0:
                    raise CalculationError("Use magnitude positiva e operação DESCONTO")
                total += value if operation == "SOMAR" else -value
                considered.append(dict(id=c.id, tipo=kind, valor=str(value), operacao=operation))
        ignored = [c for c in components if c.tipo not in used]
        return memory("COMPOSICAO_DETALHADA", base, total, parameters, considered, ignored)


def memory(strategy, base, result, parameters, considered, ignored):
    try:
        rounded = result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise CalculationError("Resultado excede a precisão monetária") from None
    if rounded < 0 or rounded >= Decimal("1000000000000"):
        raise CalculationError("Resultado fora do intervalo monetário suportado")
    return dict(estrategia=strategy, valor_base=str(base), parametros=parameters,
                arredondamento="ROUND_HALF_UP", casas_decimais=2,
                componentes_considerados=considered,
                componentes_ignorados=[dict(id=c.id, tipo=c.tipo, valor=str(c.valor) if c.valor is not None else None) for c in ignored],
                resultado_sem_arredondamento=str(result), resultado=str(rounded))


STRATEGIES = {"VALOR_INTEGRAL": IntegralValueStrategy(), "COEFICIENTE": CoefficientStrategy(),
              "COMPOSICAO_DETALHADA": DetailedCompositionStrategy()}
