"""Testes isolados, sem conexão com PostgreSQL."""
import unittest
from datetime import date, datetime
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.services import EntityNotFoundError

ENTITIES = (
    ("Localidade", dict(codigo_localidade="TEST", estado="PE", municipio="Teste", regiao="Nordeste")),
    ("Prefixo", dict(codigo_prefixo="TEST", nome="Teste", tipo_prefixo="agencia", situacao="ativo", id_localidade=1)),
    ("Concessionaria", dict(cnpj="00000000000000", razao_social="Teste", tipo_servico="energia")),
    ("ContaConsumo", dict(competencia="2026-01", data_vencimento=date(2026, 1, 1), valor_original="1.00", categoria="energia", situacao="pendente", id_prefixo=1, id_concessionaria=1)),
    ("Documento", dict(tipo_documento="conta", formato="pdf", data_recebimento=datetime(2026, 1, 1), origem="upload", caminho_arquivo="/teste.pdf", id_conta=1)),
    ("ExtracaoInteligente", dict(data_processamento=datetime(2026, 1, 1), situacao_validacao="pendente", id_documento=1)),
    ("DadoExtraido", dict(campo_identificado="valor", situacao_validacao="pendente", id_extracao=1)),
    ("RegraCalculo", dict(nome_regra="Teste", categoria="energia", versao="1", data_inicio_vigencia=date(2026, 1, 1), situacao="ativa")),
    ("ItemRegra", dict(nome_item="Desconto", tipo_item="percentual", valor_percentual="5.000000", ordem_aplicacao=1, id_regra=1)),
    ("Calculo", dict(data_calculo=datetime(2026, 1, 1), valor_inicial="100.00", valor_calculado="95.00", situacao="concluido", id_conta=1, id_regra=1)),
)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        models.Base.metadata.create_all(self.engine)
        self.session = Session(self.engine, autoflush=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)

    def seed(self):
        for name, payload in ENTITIES:
            getattr(services, name + "Service")(self.session).create(getattr(schemas, name + "Create")(**payload))

    def test_crud_and_commits_for_all_entities(self):
        for name, payload in ENTITIES:
            with self.subTest(entity=name):
                service = getattr(services, name + "Service")(self.session)
                with patch.object(self.session, "commit", wraps=self.session.commit) as commit:
                    instance = service.create(getattr(schemas, name + "Create")(**payload))
                    commit.assert_called_once_with()
                self.assertIsInstance(instance, getattr(models, name))
                with Session(self.engine) as reader:
                    self.assertIsNotNone(reader.get(getattr(models, name), 1))
                with patch.object(self.session, "commit", wraps=self.session.commit) as commit:
                    self.assertIs(service.get_by_id(1), instance)
                    self.assertEqual(service.list(), [instance])
                    self.assertEqual(service.list(offset=1, limit=1), [])
                    commit.assert_not_called()
                field = next(iter(payload))
                changed = datetime(2026, 2, 1) if isinstance(payload[field], datetime) else "alterado"
                with patch.object(self.session, "commit", wraps=self.session.commit) as commit:
                    service.update(1, getattr(schemas, name + "Update")(**{field: changed}))
                    commit.assert_called_once_with()
                self.session.rollback()
                self.assertEqual(getattr(service.get_by_id(1), field), changed)
        for name, _ in reversed(ENTITIES):
            service = getattr(services, name + "Service")(self.session)
            with patch.object(self.session, "commit", wraps=self.session.commit) as commit:
                self.assertTrue(service.delete(1))
                commit.assert_called_once_with()
            self.session.rollback()
            self.assertEqual(service.list(), [])

    def test_missing_records(self):
        for name, _ in ENTITIES:
            service = getattr(services, name + "Service")(self.session)
            for operation in (lambda: service.get_by_id(999), lambda: service.update(999, getattr(schemas, name + "Update")()), lambda: service.delete(999)):
                with self.subTest(entity=name), self.assertRaises(EntityNotFoundError) as error:
                    operation()
                self.assertEqual(error.exception.entity, name)
                self.assertEqual(error.exception.entity_id, 999)

    def test_foreign_keys_on_create_and_update(self):
        self.seed()
        for name, payload in ENTITIES:
            service = getattr(services, name + "Service")(self.session)
            for field, repo in service.foreign_keys.items():
                for value in (999, None):
                    for operation in ("create", "update"):
                        if operation == "create" and value is None:
                            continue  # Create já rejeita None no Pydantic.
                        with self.subTest(entity=name, field=field, value=value, operation=operation):
                            data = getattr(schemas, name + ("Create" if operation == "create" else "Update"))(**({**payload, field: value} if operation == "create" else {field: value}))
                            with patch.object(service.repository, operation, wraps=getattr(service.repository, operation)) as write, patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback, self.assertRaises(EntityNotFoundError) as error:
                                service.create(data) if operation == "create" else service.update(1, data)
                            write.assert_not_called()
                            rollback.assert_called_once_with()
                            self.assertEqual(error.exception.entity, repo.model.__name__)
                            self.assertEqual(getattr(service.get_by_id(1), field), payload[field])

    def test_valid_foreign_key_changes(self):
        self.seed()
        for name, _ in ENTITIES:
            service = getattr(services, name + "Service")(self.session)
            for field, repo in service.foreign_keys.items():
                parent_name = repo.model.__name__
                payload = next(p for n, p in ENTITIES if n == parent_name).copy()
                for unique in ("codigo_localidade", "codigo_prefixo", "cnpj"):
                    if unique in payload:
                        payload[unique] += "2"
                getattr(services, parent_name + "Service")(self.session).create(getattr(schemas, parent_name + "Create")(**payload))
                service.update(1, getattr(schemas, name + "Update")(**{field: 2}))
                self.assertEqual(getattr(service.get_by_id(1), field), 2)

    def test_partial_updates_and_explicit_null(self):
        service = services.LocalidadeService(self.session)
        service.create(schemas.LocalidadeCreate(**ENTITIES[0][1]))
        service.update(1, schemas.LocalidadeUpdate(municipio="Outro"))
        self.assertEqual(service.get_by_id(1).regiao, "Nordeste")
        service.update(1, schemas.LocalidadeUpdate(regiao=None))
        self.assertIsNone(service.get_by_id(1).regiao)

    def test_integrity_errors_rollback_and_session_recovery(self):
        service = services.LocalidadeService(self.session)
        service.create(schemas.LocalidadeCreate(**ENTITIES[0][1]))
        for operation in (lambda: service.create(schemas.LocalidadeCreate(**ENTITIES[0][1])), lambda: service.update(1, schemas.LocalidadeUpdate(municipio=None))):
            with self.assertRaises(IntegrityError):
                operation()
            self.assertEqual(service.get_by_id(1).municipio, "Teste")
            self.assertEqual(len(service.list()), 1)
        service.update(1, schemas.LocalidadeUpdate(municipio="Recuperado"))
        self.assertEqual(service.get_by_id(1).municipio, "Recuperado")

    def test_delete_with_dependents_rolls_back(self):
        self.seed()
        service = services.LocalidadeService(self.session)
        with self.assertRaises(IntegrityError):
            service.delete(1)
        self.assertIsNotNone(service.get_by_id(1))
        self.assertEqual(services.PrefixoService(self.session).get_by_id(1).id_localidade, 1)

    def test_calculation_services_integrity_rollback_and_recovery(self):
        self.seed()
        for name, payload in ENTITIES[-3:]:
            service = getattr(services, name + "Service")(self.session)
            field = next(iter(payload))
            with self.subTest(entity=name), patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback, self.assertRaises(IntegrityError):
                service.update(1, getattr(schemas, name + "Update")(**{field: None}))
            rollback.assert_called_once_with()
            self.assertEqual(getattr(service.get_by_id(1), field), payload[field])
            service.update(1, getattr(schemas, name + "Update")(situacao="recuperado") if name != "ItemRegra" else schemas.ItemRegraUpdate(descricao="recuperado"))

    def test_regra_delete_with_dependents_rolls_back(self):
        self.seed()
        service = services.RegraCalculoService(self.session)
        with patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback, self.assertRaises(IntegrityError):
            service.delete(1)
        rollback.assert_called_once_with()
        self.assertIsNotNone(service.get_by_id(1))
        self.assertEqual(services.ItemRegraService(self.session).get_by_id(1).id_regra, 1)
        self.assertEqual(services.CalculoService(self.session).get_by_id(1).id_regra, 1)

    def test_commit_failure_rolls_back_every_write(self):
        self.seed()
        for name, payload in ENTITIES:
            service = getattr(services, name + "Service")(self.session)
            for operation in ("update", "create"):
                new_payload = payload.copy()
                for unique in ("codigo_localidade", "codigo_prefixo", "cnpj"):
                    if unique in new_payload:
                        new_payload[unique] += "2"
                data = getattr(schemas, name + ("Create" if operation == "create" else "Update"))(**(new_payload if operation == "create" else {}))
                with self.subTest(entity=name, operation=operation), patch.object(self.session, "commit", side_effect=RuntimeError("commit falhou")), patch.object(self.session, "rollback", wraps=self.session.rollback) as rollback, self.assertRaisesRegex(RuntimeError, "commit falhou"):
                    service.create(data) if operation == "create" else service.update(1, data)
                rollback.assert_called_once_with()
                self.assertEqual(len(service.list()), 1)
        for name, _ in reversed(ENTITIES):
            service = getattr(services, name + "Service")(self.session)
            with self.subTest(entity=name), patch.object(self.session, "commit", side_effect=RuntimeError("commit falhou")), self.assertRaises(RuntimeError):
                service.delete(1)
            self.assertIsNotNone(service.get_by_id(1))
            service.delete(1)


if __name__ == "__main__":
    unittest.main()
