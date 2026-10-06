"""Endpoints com SQLite em memória; nenhuma conexão com PostgreSQL."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.main import app
from app.models import Base


LOCALIDADE = dict(codigo_localidade="TEST", estado="PE", municipio="Recife", regiao="Nordeste")
ENTITIES = (
    ("localidades", "id_localidade", LOCALIDADE, {"municipio": "Olinda"}),
    ("prefixos", "id_prefixo", dict(codigo_prefixo="TEST", nome="Teste", tipo_prefixo="agencia", situacao="ativo", id_localidade=1), {"nome": "Outro"}),
    ("concessionarias", "id_concessionaria", dict(cnpj="00000000000000", razao_social="Teste", nome_fantasia="Teste", tipo_servico="energia"), {"razao_social": "Outra"}),
    ("contas_consumo", "id_conta", dict(numero_conta="123", competencia="2026-10", data_emissao=None, data_vencimento="2026-10-20", valor_original="123.45", codigo_barras=None, consumo="10.500", unidade_consumo="kWh", categoria="energia", situacao="pendente", id_prefixo=1, id_concessionaria=1), {"situacao": "validada"}),
    ("documentos", "id_documento", dict(tipo_documento="fatura", formato="pdf", data_recebimento="2026-10-06T10:00:00", origem="manual", caminho_arquivo="contas/fatura.pdf", id_conta=1), {"caminho_arquivo": "contas/revisada.pdf"}),
    ("extracoes_inteligentes", "id_extracao", dict(data_processamento="2026-10-06T11:00:00", nivel_confianca="95.50", situacao_validacao="pendente", id_documento=1), {"situacao_validacao": "validada"}),
    ("dados_extraidos", "id_dado_extraido", dict(campo_identificado="valor_original", valor_extraido="123.45", nivel_confianca="98.50", situacao_validacao="pendente", valor_validado=None, id_extracao=1), {"valor_validado": "123.45", "situacao_validacao": "validada"}),
    ("regras_calculo", "id_regra", dict(nome_regra="Regra teste", categoria="energia", versao="1", data_inicio_vigencia="2026-10-01", data_fim_vigencia=None, situacao="ativa"), {"nome_regra": "Regra revisada"}),
    ("itens_regra", "id_item_regra", dict(nome_item="Desconto", tipo_item="percentual", valor_percentual="5.000000", ordem_aplicacao=1, descricao=None, id_regra=1), {"ordem_aplicacao": 2}),
    ("calculos", "id_calculo", dict(data_calculo="2026-10-06T12:00:00", valor_inicial="123.45", valor_calculado="117.28", situacao="pendente", id_conta=1, id_regra=1), {"situacao": "validado"}),
)


class ApiTestCase(unittest.TestCase):
    """Infraestrutura compartilhada: banco novo e overrides isolados por teste."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        factory = sessionmaker(bind=self.engine, autoflush=False)

        def override_db():
            with factory() as session:
                yield session

        previous_overrides = app.dependency_overrides.copy()
        self.addCleanup(self.restore_overrides, previous_overrides)
        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def restore_overrides(self, overrides):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)


class ApiTests(ApiTestCase):
    def test_crud_for_each_entity(self):
        for resource, id_field, payload, changes in ENTITIES:
            with self.subTest(resource=resource):
                url = "/api/v1/" + resource
                self.assertEqual(self.client.get(url).json(), [])
                created = self.client.post(url, json=payload)
                self.assertEqual(created.status_code, 201, created.text)
                expected = {**payload, id_field: created.json()[id_field]}
                self.assertEqual(created.json(), expected)
                detail_url = f"{url}/{expected[id_field]}"
                listed = self.client.get(url)
                self.assertEqual(listed.status_code, 200)
                self.assertEqual(listed.json(), [expected])
                self.assertEqual(self.client.get(url, params={"offset": 1, "limit": 1}).json(), [])
                fetched = self.client.get(detail_url)
                self.assertEqual(fetched.status_code, 200)
                self.assertEqual(fetched.json(), expected)
                updated = self.client.patch(detail_url, json=changes)
                self.assertEqual(updated.status_code, 200, updated.text)
                expected.update(changes)
                self.assertEqual(updated.json(), expected)
                self.assertEqual(self.client.get(detail_url).json(), expected)
        for resource, _, _, _ in reversed(ENTITIES):
            with self.subTest(delete=resource):
                url = "/api/v1/" + resource
                deleted = self.client.delete(url + "/1")
                self.assertEqual(deleted.status_code, 204)
                self.assertEqual(deleted.content, b"")
                self.assertEqual(self.client.get(url).json(), [])
                self.assertEqual(self.client.get(url + "/1").status_code, 404)

    def test_missing_entities(self):
        for resource, _, _, changes in ENTITIES:
            url = f"/api/v1/{resource}/999"
            for method, kwargs in (("get", {}), ("patch", {"json": changes}), ("delete", {})):
                with self.subTest(resource=resource, method=method):
                    response = getattr(self.client, method)(url, **kwargs)
                    self.assertEqual(response.status_code, 404)
                    self.assertIn("999", response.json()["detail"])

    def test_missing_localidade_on_prefixo_create_and_update(self):
        payload = ENTITIES[1][2]
        response = self.client.post("/api/v1/prefixos", json={**payload, "id_localidade": 999})
        self.assertEqual(response.status_code, 404)
        self.assertIn("Localidade", response.json()["detail"])
        self.assertEqual(self.client.get("/api/v1/prefixos").json(), [])
        self.assertEqual(self.client.post("/api/v1/localidades", json=LOCALIDADE).status_code, 201)
        self.assertEqual(self.client.post("/api/v1/prefixos", json=payload).status_code, 201)
        response = self.client.patch("/api/v1/prefixos/1", json={"id_localidade": 999})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get("/api/v1/prefixos/1").json()["id_localidade"], 1)

    def test_explicit_null_in_partial_update(self):
        self.client.post("/api/v1/localidades", json=LOCALIDADE)
        response = self.client.patch("/api/v1/localidades/1", json={"regiao": None})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {**LOCALIDADE, "id_localidade": 1, "regiao": None})

    def create_entity_chain(self):
        for resource, _, payload, _ in ENTITIES:
            response = self.client.post("/api/v1/" + resource, json=payload)
            self.assertEqual(response.status_code, 201, response.text)

    def test_missing_foreign_keys_for_new_entities(self):
        self.create_entity_chain()
        references = (
            (3, "id_prefixo", "Prefixo"),
            (3, "id_concessionaria", "Concessionaria"),
            (4, "id_conta", "ContaConsumo"),
            (5, "id_documento", "Documento"),
            (6, "id_extracao", "ExtracaoInteligente"),
        )
        for index, field, entity in references:
            resource, _, payload, _ = ENTITIES[index]
            url = "/api/v1/" + resource
            before = self.client.get(url).json()
            for method, target, data in (
                ("post", url, {**payload, field: 999}),
                ("patch", url + "/1", {field: 999}),
            ):
                with self.subTest(resource=resource, field=field, method=method):
                    response = getattr(self.client, method)(target, json=data)
                    self.assertEqual(response.status_code, 404, response.text)
                    self.assertIn(entity, response.json()["detail"])
                    self.assertIn("999", response.json()["detail"])
                    self.assertEqual(self.client.get(url).json(), before)

    def test_explicit_null_for_new_entities(self):
        self.create_entity_chain()
        for resource, field in (
            ("contas_consumo", "numero_conta"),
            ("extracoes_inteligentes", "nivel_confianca"),
            ("dados_extraidos", "valor_extraido"),
        ):
            with self.subTest(resource=resource):
                url = f"/api/v1/{resource}/1"
                before = self.client.get(url).json()
                response = self.client.patch(url, json={field: None})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), {**before, field: None})
                self.assertEqual(self.client.get(url).json(), response.json())

    def test_schema_and_pagination_validation(self):
        for resource, _, payload, _ in ENTITIES:
            url = "/api/v1/" + resource
            with self.subTest(resource=resource):
                self.assertEqual(self.client.post(url, json={}).status_code, 422)
                self.assertEqual(self.client.post(url, json={**payload, "unknown": True}).status_code, 422)
                self.assertEqual(self.client.patch(url + "/1", json={"unknown": True}).status_code, 422)
                self.assertEqual(self.client.get(url, params={"offset": -1}).status_code, 422)
                self.assertEqual(self.client.get(url, params={"limit": 0}).status_code, 422)

    def assert_missing_calculation_fk(self, index, field, entity):
        self.create_entity_chain()
        resource, _, payload, _ = ENTITIES[index]
        url = "/api/v1/" + resource
        before = self.client.get(url).json()
        for method, target, data in (
            ("post", url, {**payload, field: 999}),
            ("patch", url + "/1", {field: 999}),
        ):
            with self.subTest(method=method):
                response = getattr(self.client, method)(target, json=data)
                self.assertEqual(response.status_code, 404, response.text)
                self.assertIn(entity, response.json()["detail"])
                self.assertIn("999", response.json()["detail"])
                self.assertEqual(self.client.get(url).json(), before)

    def test_missing_regra_on_item_create_and_update(self):
        self.assert_missing_calculation_fk(8, "id_regra", "RegraCalculo")

    def test_missing_regra_on_calculo_create_and_update(self):
        self.assert_missing_calculation_fk(9, "id_regra", "RegraCalculo")

    def test_missing_conta_on_calculo_create_and_update(self):
        self.assert_missing_calculation_fk(9, "id_conta", "ContaConsumo")

    def test_existing_root_and_health(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "API BB Contas IA funcionando"})
        with patch("app.main.test_database_connection", return_value=1):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "connected"})

    def test_session_dependency_closes_without_managing_transactions(self):
        with patch("app.api.dependencies.SessionLocal") as factory:
            session = factory.return_value.__enter__.return_value
            dependency = get_db()
            self.assertIs(next(dependency), session)
            dependency.close()
            factory.return_value.__exit__.assert_called_once()
            session.commit.assert_not_called()
            session.rollback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
