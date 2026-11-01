"""Seed pela API real em SQLite; fixtures simuladas, sem IA e sem rede."""
import contextlib
import io
import json
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.exceptions import ContextoOperacionalError
from app.services.validacao_documental import ValidacaoDocumentalService
from scripts.seed_demo import prepare, FIXTURES
from tests.test_api import ApiTestCase


class DemoSeedTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.network = patch('socket.socket.connect', side_effect=AssertionError('Rede proibida na DEMO'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.manifest = self.seed()
        self.cases = {c['nome']: c for c in json.loads(FIXTURES.read_text())}

    def seed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return prepare(self.client, 'teste')

    def snapshot(self):
        with Session(self.engine) as s:
            return {table.name: [dict(r) for r in s.execute(table.select()).mappings()]
                    for table in models.Base.metadata.sorted_tables}

    def evaluate(self, name, **changes):
        case = self.cases[name]
        with Session(self.engine) as s:
            return ValidacaoDocumentalService(s).avaliar(
                {**case['leitura'], **changes},
                self.manifest['usuarios'][case['usuario']]['id_usuario'],
                self.manifest['prefixos'][case['prefixo']]['id_prefixo'])

    def test_repeated_seed_preserves_every_row_and_history(self):
        before = self.snapshot()
        self.assertEqual(self.seed(), self.manifest)
        self.assertEqual(self.snapshot(), before)

    def test_seed_reuses_equivalent_localities(self):
        self.seed()
        rows = self.client.get('/api/v1/localidades').json()
        self.assertEqual(sorted((r['municipio'], r['estado']) for r in rows),
                         [('Paulista', 'PE'), ('Recife', 'PE')])

    def test_energy_recife(self):
        self.assertEqual(self.evaluate('energia-recife')[0], 'VALIDO')

    def test_energy_paulista(self):
        self.assertEqual(self.evaluate('energia-paulista')[0], 'VALIDO')

    def test_water_both_cities(self):
        for name in ('agua-recife', 'agua-paulista'):
            with self.subTest(name=name):
                self.assertEqual(self.evaluate(name)[0], 'VALIDO')

    def test_wrong_municipality(self):
        self.assertEqual(self.evaluate('prefixo-errado')[0], 'DIVERGENCIA_PREFIXO')

    def test_other_state(self):
        self.assertEqual(self.evaluate('outra-uf')[0], 'REGIAO_NAO_SUPORTADA')

    def test_unsupported_document(self):
        for kind in ('BOLETO', 'COMPROVANTE', 'NOTA_FISCAL', 'OUTRO'):
            with self.subTest(kind=kind):
                self.assertEqual(self.evaluate('documento-incorreto', tipo_documento=kind)[0],
                                 'DOCUMENTO_NAO_SUPORTADO')

    def test_insufficient_evidence(self):
        self.assertEqual(self.evaluate('evidencia-insuficiente')[0], 'EVIDENCIA_INSUFICIENTE')

    def test_wrong_unit(self):
        self.assertEqual(self.evaluate('unidade-outro-prefixo')[0], 'DIVERGENCIA_PREFIXO')

    def test_unknown_unit(self):
        self.assertEqual(self.evaluate('energia-recife', unidade_consumidora='UC-DEMO-AUSENTE')[0],
                         'EVIDENCIA_INSUFICIENTE')

    def test_unique_utility_and_correct_unit_in_evidence(self):
        status, _, evidence = self.evaluate('energia-recife')
        self.assertEqual(status, 'VALIDO')
        self.assertEqual(evidence['id_concessionaria'],
                         self.manifest['concessionarias']['energia']['id_concessionaria'])
        with Session(self.engine) as s:
            unit = s.get(models.UnidadeConsumidora, evidence['id_unidade_consumidora'])
            self.assertEqual(unit.unidade_consumidora, 'UC-REC-ENERGIA-DEMO-001')
            self.assertEqual(unit.id_prefixo, self.manifest['prefixos']['REC-DEMO']['id_prefixo'])

    def test_unknown_utility(self):
        self.assertEqual(self.evaluate('concessionaria-desconhecida')[0], 'EVIDENCIA_INSUFICIENTE')

    def test_ambiguous_utility(self):
        with Session(self.engine) as s:
            s.add(models.Concessionaria(cnpj='DEMO-TEST-AMBIGUO',
                  razao_social='ENERGIA DEMO PE', tipo_servico='energia'))
            s.commit()
        self.assertEqual(self.evaluate('energia-recife')[0], 'EVIDENCIA_INSUFICIENTE')
        with self.assertRaises(RuntimeError), contextlib.redirect_stdout(io.StringIO()):
            self.seed()

    def test_unauthorized_prefix_refused_before_persistence(self):
        case = self.cases['energia-paulista']
        account = next(r for r in self.client.get('/api/v1/contas_consumo').json()
                       if r['numero_conta'] == 'DEMO-DOC-teste-energia-paulista')
        doc = next(r for r in self.client.get('/api/v1/documentos').json()
                   if r['id_conta'] == account['id_conta'])
        before = self.snapshot()
        response = self.client.post(f'/api/v1/documentos/{doc["id_documento"]}/interpretacao', json={
            'leitura': case['leitura'], 'contexto': {
                'id_usuario': self.manifest['usuarios']['maker']['id_usuario'],
                'id_prefixo': self.manifest['prefixos']['PAU-DEMO']['id_prefixo']}})
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.snapshot(), before)

    def test_multi_prefix_requires_selection_and_accepts_both(self):
        user = self.manifest['usuarios']['maker-multi']['id_usuario']
        with Session(self.engine) as s:
            ctx = ContextoOperacionalService(s)
            with self.assertRaises(ContextoOperacionalError):
                ctx.resolver(user)
            for prefix in self.manifest['prefixos'].values():
                self.assertEqual(ctx.resolver(user, prefix['id_prefixo']).id_prefixo, prefix['id_prefixo'])
            legacy = s.scalar(select(models.Prefixo).where(models.Prefixo.codigo_prefixo == 'DEMO'))
            with self.assertRaises(ContextoOperacionalError):
                ctx.resolver(user, legacy.id_prefixo)
        self.assertEqual(self.evaluate('multi-recife')[0], 'VALIDO')
        self.assertEqual(self.evaluate('multi-paulista')[0], 'VALIDO')

    def test_active_links_and_one_principal_per_user(self):
        for user in self.manifest['usuarios'].values():
            links = self.client.get(f'/api/v1/usuarios/{user["id_usuario"]}/prefixos').json()['vinculos']
            self.assertTrue(any(l['ativo'] for l in links))
            self.assertEqual(sum(l['principal'] for l in links), 1)
            self.assertTrue(all(l['ativo'] for l in links if l['principal']))

    def approval(self, role):
        return self.client.post('/api/v1/aprovacoes', json={
            'id_ordem': self.manifest['ordem']['id_ordem'],
            'id_usuario': self.manifest['usuarios'][role]['id_usuario'],
            'decisao': 'aprovado', 'data_hora': '2026-10-01T12:00:00'})

    def test_maker_cannot_approve_own_order(self):
        self.assertEqual(self.approval('maker').status_code, 409)

    def test_checker_can_approve(self):
        response = self.approval('checker')
        self.assertEqual(response.status_code, 201, response.text)
        order = self.client.get(f'/api/v1/ordens_pagamento/{self.manifest["ordem"]["id_ordem"]}').json()
        self.assertEqual(order['situacao'], 'aprovada')

    def test_low_limit_cannot_approve(self):
        self.assertEqual(self.approval('limite-baixo').status_code, 403)

    def test_synthetic_cnpj_check_digits(self):
        for utility in self.manifest['concessionarias'].values():
            value = utility['cnpj']
            self.assertTrue(value.startswith('00000000'))
            for size, weights in [(12, [5,4,3,2,9,8,7,6,5,4,3,2]),
                                  (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])]:
                remainder = sum(int(n)*w for n,w in zip(value[:size], weights)) % 11
                self.assertEqual(int(value[size]), 0 if remainder < 2 else 11-remainder)
