"""Schemas e CRUD de pagamentos com SQLite em memória e FKs habilitadas."""
import importlib
import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, repositories, schemas, services
from app.services import EntityNotFoundError
from tests.test_services import ENTITIES as EXISTING_ENTITIES


ENTITIES = (
    ("alcada", "Alcada", "id_alcada", dict(nome_nivel="Nivel", limite_financeiro="123.45", data_inicio_vigencia=date(2026, 10, 1))),
    ("usuario", "Usuario", "id_usuario", dict(matricula="TEST", nome="Teste", funcao="teste", situacao="livre", id_alcada=1, id_prefixo=1)),
    ("sistema_pagamento", "SistemaPagamento", "id_sistema", dict(nome="Sistema", situacao="livre")),
    ("ordem_pagamento", "OrdemPagamento", "id_ordem", dict(data_criacao=datetime(2026, 10, 6, 10), data_prevista_pagamento=date(2026, 10, 20), valor_total="150.23", situacao="livre", id_calculo=1, id_sistema=1, id_usuario_criador=1)),
    ("item_pagamento", "ItemPagamento", "id_item_pagamento", dict(codigo_evento="evento-livre", valor="150.23", id_ordem=1)),
    ("aprovacao", "Aprovacao", "id_aprovacao", dict(data_hora=datetime(2026, 10, 6, 11), decisao="decisao-livre", id_ordem=1, id_usuario=1)),
)


def create_schema(name, payload):
    return getattr(schemas, name + "Create")(**payload)


def update_schema(name, payload):
    return getattr(schemas, name + "Update")(**payload)


def changes(payload):
    field = next(iter(payload))
    return {field: datetime(2026, 11, 1) if isinstance(payload[field], datetime) else "alterado"}


class PagamentoSchemaTests(unittest.TestCase):
    def test_exports_and_model_fields(self):
        for module, name, pk, payload in ENTITIES:
            with self.subTest(entity=name):
                for layer, suffixes in ((schemas, ("Base", "Create", "Update", "Read")), (repositories, ("Repository",)), (services, ("Service",))):
                    for suffix in suffixes:
                        exported = getattr(layer, name + suffix)
                        self.assertIn(name + suffix, layer.__all__)
                        self.assertIs(exported, getattr(importlib.import_module(layer.__name__ + "." + module), name + suffix))
                columns = {column.key for column in inspect(getattr(models, name)).columns}
                self.assertEqual(set(getattr(schemas, name + "Base").model_fields), columns - {pk})
                self.assertEqual(set(getattr(schemas, name + "Read").model_fields), columns)
                self.assertEqual(set(getattr(schemas, name + "Update").model_fields), columns - {pk})

    def test_required_fields_extra_forbidden_and_partial_updates(self):
        for _, name, pk, payload in ENTITIES:
            with self.subTest(entity=name):
                create = getattr(schemas, name + "Create")
                update = getattr(schemas, name + "Update")
                validated = create(**payload)
                for field, info in create.model_fields.items():
                    if info.is_required():
                        with self.subTest(field=field), self.assertRaises(ValidationError):
                            create(**{k: v for k, v in payload.items() if k != field})
                        with self.assertRaises(ValidationError):
                            create(**{**payload, field: None})
                for field in (pk, "unknown"):
                    with self.assertRaises(ValidationError):
                        create(**payload, **{field: 1})
                    with self.assertRaises(ValidationError):
                        update(**{field: 1})
                self.assertEqual(update().model_dump(exclude_unset=True), {})
                for field, value in validated.model_dump().items():
                    self.assertEqual(update(**{field: value}).model_dump(exclude_unset=True), {field: value})
                    self.assertEqual(update(**{field: None}).model_dump(exclude_unset=True), {field: None})

    def test_read_from_attributes_and_decimal_date_datetime_types(self):
        for _, name, pk, payload in ENTITIES:
            with self.subTest(entity=name):
                data = create_schema(name, payload).model_dump()
                row = getattr(models, name)(**data, **{pk: 42})
                read = getattr(schemas, name + "Read")
                self.assertTrue(read.model_config["from_attributes"])
                self.assertEqual(read.model_validate(row).model_dump(), {**data, pk: 42})
                with self.assertRaises(ValidationError):
                    read(**data)
        alcada = schemas.AlcadaCreate(nome_nivel="Livre", limite_financeiro="0.01", data_inicio_vigencia="2026-10-01", data_fim_vigencia="2026-12-31")
        self.assertEqual(alcada.limite_financeiro, Decimal("0.01"))
        self.assertEqual(alcada.data_inicio_vigencia, date(2026, 10, 1))
        self.assertEqual(alcada.data_fim_vigencia, date(2026, 12, 31))
        ordem = create_schema("OrdemPagamento", {**ENTITIES[3][3], "data_criacao": "2026-10-06T10:00:00", "data_prevista_pagamento": "2026-10-20"})
        self.assertIsInstance(ordem.data_criacao, datetime)
        self.assertIsInstance(ordem.data_prevista_pagamento, date)
        self.assertEqual(ordem.valor_total, Decimal("150.23"))
        self.assertEqual(create_schema("ItemPagamento", ENTITIES[4][3]).valor, Decimal("150.23"))


class PagamentoDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        models.Base.metadata.create_all(self.engine)
        self.session = Session(self.engine, autoflush=False)
        self.addCleanup(self.session.close)
        for name, payload in EXISTING_ENTITIES:
            getattr(services, name + "Service")(self.session).create(create_schema(name, payload))

    def seed(self):
        for _, name, _, payload in ENTITIES:
            getattr(services, name + "Service")(self.session).create(create_schema(name, payload))

    def test_services_crud_commits_and_partial_update(self):
        for _, name, pk, payload in ENTITIES:
            with self.subTest(entity=name):
                service = getattr(services, name + "Service")(self.session)
                with patch.object(self.session, "commit", wraps=self.session.commit) as commit:
                    row = service.create(create_schema(name, payload))
                    commit.assert_called_once_with()
                entity_id = getattr(row, pk)
                expected = create_schema(name, payload).model_dump()
                with Session(self.engine) as reader:
                    self.assertIsNotNone(reader.get(getattr(models, name), entity_id))
                with patch.object(self.session, "commit", wraps=self.session.commit) as commit:
                    self.assertIs(service.get_by_id(entity_id), row)
                    self.assertEqual(service.list(), [row])
                    self.assertEqual(service.list(offset=1, limit=1), [])
                    commit.assert_not_called()
                delta = changes(payload)
                with patch.object(self.session, "commit", wraps=self.session.commit) as commit:
                    self.assertIs(service.update(entity_id, update_schema(name, delta)), row)
                    commit.assert_called_once_with()
                self.session.expire_all()
                for field, value in {**expected, **delta}.items():
                    self.assertEqual(getattr(service.get_by_id(entity_id), field), value)
        for _, name, _, _ in reversed(ENTITIES):
            service = getattr(services, name + "Service")(self.session)
            with patch.object(self.session, "commit", wraps=self.session.commit) as commit:
                self.assertTrue(service.delete(1))
                commit.assert_called_once_with()
            self.assertEqual(service.list(), [])
            with self.assertRaises(EntityNotFoundError):
                service.get_by_id(1)

    def test_repositories_crud_flush_without_transaction_control(self):
        created = []
        with patch.object(self.session, "commit", wraps=self.session.commit) as commit, patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback, patch.object(self.session, "flush", wraps=self.session.flush) as flush:
            for _, name, pk, payload in ENTITIES:
                with self.subTest(entity=name):
                    repo = getattr(repositories, name + "Repository")(self.session)
                    row = repo.create(create_schema(name, payload))
                    entity_id = getattr(row, pk)
                    self.assertIsInstance(entity_id, int)
                    self.assertIs(repo.get_by_id(entity_id), row)
                    self.assertEqual(repo.list(), [row])
                    self.assertIs(repo.update(entity_id, update_schema(name, changes(payload))), row)
                    self.assertIsNone(repo.get_by_id(999))
                    self.assertIsNone(repo.update(999, update_schema(name, {})))
                    self.assertFalse(repo.delete(999))
                    created.append(repo)
            for repo in reversed(created):
                self.assertTrue(repo.delete(1))
                self.assertEqual(repo.list(), [])
            self.assertEqual(flush.call_count, 18)
            commit.assert_not_called()
            rollback.assert_not_called()

    def test_repository_writes_can_be_rolled_back(self):
        self.seed()
        for _, name, pk, payload in ENTITIES:
            repo = getattr(repositories, name + "Repository")(self.session)
            with self.subTest(entity=name):
                repo.update(1, update_schema(name, changes(payload)))
                self.session.rollback()
                for field, value in create_schema(name, payload).model_dump().items():
                    self.assertEqual(getattr(repo.get_by_id(1), field), value)
                second_payload = {**payload}
                for unique in ("matricula", "nome"):
                    if unique in second_payload:
                        second_payload[unique] += "2"
                row = repo.create(create_schema(name, second_payload))
                entity_id = getattr(row, pk)
                self.session.rollback()
                self.assertIsNone(repo.get_by_id(entity_id))
        for _, name, _, _ in reversed(ENTITIES):
            repo = getattr(repositories, name + "Repository")(self.session)
            self.assertTrue(repo.delete(1))
            self.session.rollback()
            self.assertIsNotNone(repo.get_by_id(1))
            getattr(services, name + "Service")(self.session).delete(1)

    def assert_missing_foreign_keys(self, index):
        self.seed()
        _, name, _, payload = ENTITIES[index]
        service = getattr(services, name + "Service")(self.session)
        for field, repo in service.foreign_keys.items():
            values = (999,) if name == "Usuario" else (999, None)
            for value in values:
                for operation in ("create", "update"):
                    if operation == "create" and value is None:
                        continue
                    data = create_schema(name, {**payload, field: value}) if operation == "create" else update_schema(name, {field: value})
                    with self.subTest(field=field, operation=operation, value=value), patch.object(service.repository, operation, wraps=getattr(service.repository, operation)) as write, patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback:
                        with self.assertRaises(EntityNotFoundError) as error:
                            getattr(service, operation)(data) if operation == "create" else service.update(1, data)
                        write.assert_not_called()
                        rollback.assert_called_once_with()
                        self.assertEqual(error.exception.entity, repo.model.__name__)
                        self.assertEqual(error.exception.entity_id, value)
                        self.assertEqual(getattr(service.get_by_id(1), field), payload[field])
                        self.assertEqual(len(service.list()), 1)
        service.update(1, update_schema(name, changes(payload)))
        self.assertEqual(len(service.list()), 1)

    def test_usuario_missing_foreign_keys(self):
        self.assert_missing_foreign_keys(1)

    def test_ordem_missing_foreign_keys(self):
        self.assert_missing_foreign_keys(3)

    def test_item_missing_foreign_key(self):
        self.assert_missing_foreign_keys(4)

    def test_aprovacao_missing_foreign_keys(self):
        self.assert_missing_foreign_keys(5)

    def test_usuario_optional_foreign_keys_and_explicit_null(self):
        service = services.UsuarioService(self.session)
        required = {k: v for k, v in ENTITIES[1][3].items() if k not in ("id_alcada", "id_prefixo")}
        for optional in ({}, {"id_alcada": None, "id_prefixo": None}):
            user = service.create(schemas.UsuarioCreate(**{**required, "matricula": str(optional), **optional}))
            self.assertIsNone(user.id_alcada)
            self.assertIsNone(user.id_prefixo)
        alcada = services.AlcadaService(self.session).create(create_schema("Alcada", ENTITIES[0][3]))
        service.update(1, schemas.UsuarioUpdate(id_alcada=alcada.id_alcada, id_prefixo=1))
        service.update(1, schemas.UsuarioUpdate(nome="Outro"))
        self.assertEqual(service.get_by_id(1).id_alcada, alcada.id_alcada)
        service.update(1, schemas.UsuarioUpdate(id_alcada=None, id_prefixo=None))
        self.assertIsNone(service.get_by_id(1).id_alcada)
        self.assertIsNone(service.get_by_id(1).id_prefixo)

    def test_integrity_error_rollback_and_session_recovery_for_each_service(self):
        self.seed()
        for _, name, _, payload in ENTITIES:
            service = getattr(services, name + "Service")(self.session)
            field = next(iter(payload))
            with self.subTest(entity=name), patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback:
                with self.assertRaises(IntegrityError):
                    service.update(1, update_schema(name, {field: None}))
                rollback.assert_called_once_with()
                self.assertEqual(getattr(service.get_by_id(1), field), payload[field])
                service.update(1, update_schema(name, changes(payload)))
                self.assertEqual(getattr(service.get_by_id(1), field), changes(payload)[field])

    def test_duplicate_create_rollback_and_session_recovery(self):
        self.seed()
        for index, unique in ((1, "matricula"), (2, "nome")):
            _, name, _, payload = ENTITIES[index]
            service = getattr(services, name + "Service")(self.session)
            with self.subTest(entity=name), patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback:
                with self.assertRaises(IntegrityError):
                    service.create(create_schema(name, payload))
                rollback.assert_called_once_with()
            self.assertEqual(len(service.list()), 1)
            service.create(create_schema(name, {**payload, unique: "nova"}))
            self.assertEqual(len(service.list()), 2)

    def test_commit_failures_rollback_for_all_writes(self):
        self.seed()
        for _, name, _, payload in ENTITIES:
            service = getattr(services, name + "Service")(self.session)
            second_payload = {**payload}
            for unique in ("matricula", "nome"):
                if unique in second_payload:
                    second_payload[unique] += "2"
            for operation in (lambda: service.create(create_schema(name, second_payload)), lambda: service.update(1, update_schema(name, changes(payload)))):
                with self.subTest(entity=name), patch.object(self.session, "commit", side_effect=RuntimeError("commit falhou")), patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback:
                    with self.assertRaisesRegex(RuntimeError, "commit falhou"):
                        operation()
                    rollback.assert_called_once_with()
                self.assertEqual(len(service.list()), 1)
                for field, value in create_schema(name, payload).model_dump().items():
                    self.assertEqual(getattr(service.get_by_id(1), field), value)
        for _, name, _, _ in reversed(ENTITIES):
            service = getattr(services, name + "Service")(self.session)
            with self.subTest(entity=name), patch.object(self.session, "commit", side_effect=RuntimeError("commit falhou")), patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback:
                with self.assertRaises(RuntimeError):
                    service.delete(1)
                rollback.assert_called_once_with()
            self.assertIsNotNone(service.get_by_id(1))
            service.delete(1)

    def test_missing_records(self):
        for _, name, _, _ in ENTITIES:
            service = getattr(services, name + "Service")(self.session)
            for operation in (lambda: service.get_by_id(999), lambda: service.update(999, update_schema(name, {})), lambda: service.delete(999)):
                with self.subTest(entity=name), self.assertRaises(EntityNotFoundError) as error:
                    operation()
                self.assertEqual(error.exception.entity, name)
                self.assertEqual(error.exception.entity_id, 999)

    def test_delete_with_dependents_rollback_and_recovery(self):
        self.seed()
        service = services.OrdemPagamentoService(self.session)
        with patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback:
            with self.assertRaises(IntegrityError):
                service.delete(1)
            rollback.assert_called_once_with()
        self.assertIsNotNone(service.get_by_id(1))
        self.assertEqual(services.ItemPagamentoService(self.session).get_by_id(1).id_ordem, 1)
        services.AprovacaoService(self.session).delete(1)
        services.ItemPagamentoService(self.session).delete(1)
        self.assertTrue(service.delete(1))


if __name__ == "__main__":
    unittest.main()
