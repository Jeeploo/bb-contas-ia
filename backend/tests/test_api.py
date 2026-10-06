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
)


class ApiTests(unittest.TestCase):
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

    def test_schema_and_pagination_validation(self):
        for resource, _, payload, _ in ENTITIES:
            url = "/api/v1/" + resource
            with self.subTest(resource=resource):
                self.assertEqual(self.client.post(url, json={}).status_code, 422)
                self.assertEqual(self.client.post(url, json={**payload, "unknown": True}).status_code, 422)
                self.assertEqual(self.client.patch(url + "/1", json={"unknown": True}).status_code, 422)
                self.assertEqual(self.client.get(url, params={"offset": -1}).status_code, 422)
                self.assertEqual(self.client.get(url, params={"limit": 0}).status_code, 422)

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
