"""Execute em backend: python -m unittest discover -s tests -v."""

import importlib
import unittest
from datetime import date, datetime
from decimal import Decimal
from typing import get_args, get_type_hints

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app import models, repositories, schemas
from app.repositories.base import BaseRepository, CreateT, ModelT, UpdateT


ENTITIES = (
    ("localidade", "Localidade"),
    ("prefixo", "Prefixo"),
    ("concessionaria", "Concessionaria"),
    ("conta_consumo", "ContaConsumo"),
    ("documento", "Documento"),
    ("extracao_inteligente", "ExtracaoInteligente"),
    ("dado_extraido", "DadoExtraido"),
)


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        models.Base.metadata.create_all(self.engine)
        self.session = Session(self.engine, autoflush=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)

    def test_imports_and_type_annotations(self) -> None:
        for module, name in ENTITIES:
            with self.subTest(entity=name):
                cls = getattr(repositories, name + "Repository")
                self.assertIs(
                    cls, getattr(importlib.import_module("app.repositories." + module), name + "Repository")
                )
                self.assertEqual(
                    get_args(cls.__orig_bases__[0]),
                    (getattr(models, name), getattr(schemas, name + "Create"), getattr(schemas, name + "Update")),
                )
                self.assertIs(cls.model, getattr(models, name))
        self.assertIs(get_type_hints(BaseRepository.__init__)["session"], Session)
        self.assertIs(get_type_hints(BaseRepository.create)["data"], CreateT)
        self.assertIs(get_type_hints(BaseRepository.create)["return"], ModelT)
        self.assertIs(get_type_hints(BaseRepository.update)["data"], UpdateT)
        self.assertEqual(get_type_hints(BaseRepository.get_by_id)["return"], ModelT | None)
        self.assertEqual(get_type_hints(BaseRepository.list)["return"], list[ModelT])
        self.assertEqual(get_type_hints(BaseRepository.update)["return"], ModelT | None)
        self.assertIs(get_type_hints(BaseRepository.delete)["return"], bool)

    def test_crud_for_all_entities(self) -> None:
        # IDs gerados nesta sessão, sem registros externos ou dados reais.
        payloads = [
            dict(codigo_localidade="TEST", estado="PE", municipio="Teste"),
            dict(codigo_prefixo="TEST", nome="Teste", tipo_prefixo="teste", situacao="teste", id_localidade=1),
            dict(cnpj="00000000000000", razao_social="Teste", tipo_servico="teste"),
            dict(competencia="2026-01", data_vencimento=date(2026, 1, 1), valor_original=Decimal("1.00"), categoria="teste", situacao="teste", id_prefixo=1, id_concessionaria=1),
            dict(tipo_documento="teste", formato="pdf", data_recebimento=datetime(2026, 1, 1), origem="teste", caminho_arquivo="/teste.pdf", id_conta=1),
            dict(data_processamento=datetime(2026, 1, 1), situacao_validacao="teste", id_documento=1),
            dict(campo_identificado="teste", situacao_validacao="teste", id_extracao=1),
        ]
        created = []
        for (_, name), payload in zip(ENTITIES, payloads):
            with self.subTest(entity=name):
                repo = getattr(repositories, name + "Repository")(self.session)
                instance = repo.create(getattr(schemas, name + "Create")(**payload))
                self.assertIsInstance(instance, getattr(models, name))
                self.assertIs(repo.get_by_id(1), instance)
                self.assertIsNone(repo.get_by_id(999))
                self.assertEqual(repo.list(), [instance])
                self.assertEqual(repo.list(offset=1, limit=1), [])
                field = next(iter(payload))
                updated = "alterado" if isinstance(payload[field], str) else datetime(2026, 2, 1)
                self.assertIs(repo.update(1, getattr(schemas, name + "Update")(**{field: updated})), instance)
                self.assertEqual(getattr(instance, field), updated)
                for unchanged in payload.keys() - {field}:
                    self.assertEqual(getattr(instance, unchanged), payload[unchanged])
                self.assertIsNone(repo.update(999, getattr(schemas, name + "Update")()))
                self.assertFalse(repo.delete(999))
                created.append(repo)
        for repo in reversed(created):
            self.assertTrue(repo.delete(1))
            self.assertIsNone(repo.get_by_id(1))
            self.assertEqual(repo.list(), [])

    def test_partial_update_null_and_transaction_control(self) -> None:
        repo = repositories.LocalidadeRepository(self.session)
        instance = repo.create(schemas.LocalidadeCreate(codigo_localidade="TEST", estado="PE", municipio="Teste", regiao="Teste"))
        repo.update(instance.id_localidade, schemas.LocalidadeUpdate(municipio="Outro"))
        self.assertEqual(instance.regiao, "Teste")
        repo.update(instance.id_localidade, schemas.LocalidadeUpdate(regiao=None))
        self.assertIsNone(instance.regiao)
        self.session.rollback()
        self.assertEqual(repo.list(), [])
        instance = repo.create(schemas.LocalidadeCreate(codigo_localidade="TEST", estado="PE", municipio="Teste"))
        entity_id = instance.id_localidade
        self.session.commit()
        repo.update(entity_id, schemas.LocalidadeUpdate(municipio="Outro"))
        self.session.rollback()
        self.assertEqual(repo.get_by_id(entity_id).municipio, "Teste")
        repo.delete(entity_id)
        self.session.rollback()
        self.assertIsNotNone(repo.get_by_id(entity_id))


if __name__ == "__main__":
    unittest.main()
