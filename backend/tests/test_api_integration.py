"""Fluxo completo via HTTP, com SQLite em memória e IDs retornados pela API."""
import unittest

from sqlalchemy import text

from tests import test_api


# Cada campo aponta para o recurso pai criado anteriormente no fluxo.
FOREIGN_KEYS = {
    "itens_regra": {"id_regra": "regras_calculo"},
    "calculos": {"id_conta": "contas_consumo", "id_regra": "regras_calculo"},
    "prefixos": {"id_localidade": "localidades"},
    "contas_consumo": {
        "id_prefixo": "prefixos",
        "id_concessionaria": "concessionarias",
    },
    "documentos": {"id_conta": "contas_consumo"},
    "extracoes_inteligentes": {"id_documento": "documentos"},
    "dados_extraidos": {"id_extracao": "extracoes_inteligentes"},
}


class ApiIntegrationTests(test_api.ApiTestCase):
    def assert_resources(self, expected_by_resource, ids):
        """Confere persistência e todas as FKs em buscas e listagens."""
        for resource, expected in expected_by_resource.items():
            url = f"/api/v1/{resource}"
            with self.subTest(resource=resource, phase="read"):
                fetched = self.client.get(f"{url}/{ids[resource]}")
                self.assertEqual(fetched.status_code, 200, fetched.text)
                self.assertEqual(fetched.json(), expected)
                listed = self.client.get(url)
                self.assertEqual(listed.status_code, 200, listed.text)
                self.assertEqual(listed.json(), [expected])
                for field, parent in FOREIGN_KEYS.get(resource, {}).items():
                    self.assertEqual(fetched.json()[field], ids[parent])
                    self.assertEqual(listed.json()[0][field], ids[parent])
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("PRAGMA foreign_keys")).scalar(), 1)
            self.assertEqual(connection.execute(text("PRAGMA foreign_key_check")).all(), [])

    def test_complete_domain_flow(self):
        ids = {}
        expected_by_resource = {}
        for resource, id_field, template, _ in test_api.ENTITIES:
            url = f"/api/v1/{resource}"
            empty = self.client.get(url)
            self.assertEqual(empty.status_code, 200, empty.text)
            self.assertEqual(empty.json(), [])

            payload = template.copy()
            for field, parent in FOREIGN_KEYS.get(resource, {}).items():
                payload[field] = ids[parent]
            created = self.client.post(url, json=payload)
            self.assertEqual(created.status_code, 201, created.text)
            entity_id = created.json()[id_field]
            self.assertIsInstance(entity_id, int)
            self.assertGreater(entity_id, 0)
            ids[resource] = entity_id
            expected_by_resource[resource] = {**payload, id_field: entity_id}
            self.assertEqual(created.json(), expected_by_resource[resource])
            self.assert_resources(expected_by_resource, ids)

        # Validação de um dado extraído sem perder sua ligação com a extração.
        changes = {"valor_validado": "123.45", "situacao_validacao": "validada"}
        updated = self.client.patch(
            f"/api/v1/dados_extraidos/{ids['dados_extraidos']}", json=changes
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        expected_by_resource["dados_extraidos"].update(changes)
        self.assertEqual(updated.json(), expected_by_resource["dados_extraidos"])
        self.assert_resources(expected_by_resource, ids)

        missing_id = max(ids.values()) + 1000
        for resource, _, _, patch_payload in test_api.ENTITIES:
            url = f"/api/v1/{resource}/{missing_id}"
            for method, kwargs in (
                ("get", {}),
                ("patch", {"json": patch_payload}),
                ("delete", {}),
            ):
                with self.subTest(resource=resource, method=method, phase="missing"):
                    response = getattr(self.client, method)(url, **kwargs)
                    self.assertEqual(response.status_code, 404, response.text)
                    self.assertIn(str(missing_id), response.json()["detail"])
        self.assert_resources(expected_by_resource, ids)

        # Filhos antes dos pais, com FKs habilitadas durante todas as deleções.
        for resource, _, _, _ in reversed(test_api.ENTITIES):
            url = f"/api/v1/{resource}/{ids[resource]}"
            deleted = self.client.delete(url)
            self.assertEqual(deleted.status_code, 204, deleted.text)
            self.assertEqual(deleted.content, b"")
            self.assertEqual(self.client.get(url).status_code, 404)
            listed = self.client.get(f"/api/v1/{resource}")
            self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual(listed.json(), [])
            del expected_by_resource[resource]
            self.assert_resources(expected_by_resource, ids)


if __name__ == "__main__":
    unittest.main()
