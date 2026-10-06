"""Importação e validação dos schemas de regras e cálculos, sem banco externo."""

import importlib
import unittest
from datetime import date, datetime
from decimal import Decimal

from pydantic import ValidationError

from app import models, schemas


ENTITIES = (
    ("regra_calculo", "RegraCalculo", "id_regra", dict(
        nome_regra="Regra", categoria="energia", versao="1",
        data_inicio_vigencia="2026-10-01", situacao="ativa",
    )),
    ("item_regra", "ItemRegra", "id_item_regra", dict(
        nome_item="Desconto", tipo_item="percentual", ordem_aplicacao=1, id_regra=7,
    )),
    ("calculo", "Calculo", "id_calculo", dict(
        data_calculo="2026-10-06T10:30:00", valor_inicial="123.45",
        valor_calculado="117.2775", situacao="concluido", id_conta=3, id_regra=7,
    )),
)


class CalculoSchemaTests(unittest.TestCase):
    def test_imports(self):
        for module, name, _, _ in ENTITIES:
            for suffix in ("Base", "Create", "Update", "Read"):
                with self.subTest(schema=name + suffix):
                    self.assertIs(
                        getattr(schemas, name + suffix),
                        getattr(importlib.import_module("app.schemas." + module), name + suffix),
                    )
                    self.assertIn(name + suffix, schemas.__all__)

    def test_create_required_fields_and_rejected_ids(self):
        for _, name, primary_key, payload in ENTITIES:
            create = getattr(schemas, name + "Create")
            with self.subTest(entity=name):
                instance = create(**payload)
                self.assertNotIn(primary_key, instance.model_dump())
                for field in payload:
                    with self.subTest(missing=field), self.assertRaises(ValidationError):
                        create(**{key: value for key, value in payload.items() if key != field})
                for field in (primary_key, "unknown"):
                    with self.subTest(extra=field), self.assertRaises(ValidationError):
                        create(**payload, **{field: 1})

    def test_dates_decimals_and_nullable_fields(self):
        regra = schemas.RegraCalculoCreate(**ENTITIES[0][3])
        self.assertEqual(regra.data_inicio_vigencia, date(2026, 10, 1))
        self.assertIsNone(regra.data_fim_vigencia)
        regra = schemas.RegraCalculoCreate(**ENTITIES[0][3], data_fim_vigencia="2026-12-31")
        self.assertEqual(regra.data_fim_vigencia, date(2026, 12, 31))
        item = schemas.ItemRegraCreate(**ENTITIES[1][3])
        self.assertIsNone(item.valor_percentual)
        self.assertIsNone(item.descricao)
        item = schemas.ItemRegraCreate(**ENTITIES[1][3], valor_percentual="5.123456", descricao="Teste")
        self.assertEqual(item.valor_percentual, Decimal("5.123456"))
        calculo = schemas.CalculoCreate(**ENTITIES[2][3])
        self.assertEqual(calculo.data_calculo, datetime(2026, 10, 6, 10, 30))
        self.assertEqual(calculo.valor_inicial, Decimal("123.45"))
        self.assertEqual(calculo.valor_calculado, Decimal("117.2775"))
        self.assertIsInstance(calculo.valor_calculado, Decimal)
        self.assertIsInstance(calculo.id_conta, int)

    def test_invalid_types_and_null_required_fields(self):
        for _, name, _, payload in ENTITIES:
            create = getattr(schemas, name + "Create")
            for field in payload:
                for value in (None, []):
                    with self.subTest(entity=name, field=field, value=value):
                        with self.assertRaises(ValidationError):
                            create(**{**payload, field: value})
        for create, payload, field in (
            (schemas.RegraCalculoCreate, ENTITIES[0][3], "data_inicio_vigencia"),
            (schemas.CalculoCreate, ENTITIES[2][3], "data_calculo"),
            (schemas.CalculoCreate, ENTITIES[2][3], "valor_inicial"),
            (schemas.ItemRegraCreate, ENTITIES[1][3], "valor_percentual"),
        ):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                create(**{**payload, field: "invalido"})

    def test_partial_update_and_explicit_null(self):
        for _, name, primary_key, payload in ENTITIES:
            update = getattr(schemas, name + "Update")
            with self.subTest(entity=name):
                self.assertEqual(update().model_dump(exclude_unset=True), {})
                for field, value in payload.items():
                    partial = update(**{field: value})
                    self.assertEqual(set(partial.model_dump(exclude_unset=True)), {field})
                for field in (primary_key, "unknown"):
                    with self.subTest(extra=field), self.assertRaises(ValidationError):
                        update(**{field: 1})
        for update, field in (
            (schemas.RegraCalculoUpdate, "data_fim_vigencia"),
            (schemas.ItemRegraUpdate, "valor_percentual"),
            (schemas.ItemRegraUpdate, "descricao"),
        ):
            self.assertEqual(update(**{field: None}).model_dump(exclude_unset=True), {field: None})

    def test_read_from_sqlalchemy_attributes(self):
        for _, name, primary_key, payload in ENTITIES:
            with self.subTest(entity=name):
                validated = getattr(schemas, name + "Create")(**payload).model_dump()
                instance = getattr(models, name)(**validated, **{primary_key: 42})
                read = getattr(schemas, name + "Read")
                self.assertTrue(read.model_config["from_attributes"])
                self.assertEqual(read.model_validate(instance).model_dump(), {**validated, primary_key: 42})
                with self.assertRaises(ValidationError):
                    read(**validated)


if __name__ == "__main__":
    unittest.main()
