"""Fluxo pela API com dados fictícios, SQLite e storage temporário."""
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from sqlalchemy import text
from app.core.config import settings
from tests.test_api import ApiTestCase
from tests.test_processamento_documento import pdf

DEMO_TEXT = ('DEMONSTRACAO FICTICIA - SEM VALIDADE PARA PAGAMENTO\n'
             'Competência: 10/2026\nVencimento: 20/10/2026\n'
             'Valor total: R$ 123,45\nConsumo: 100,500 kWh\nCódigo de barras: ' + '0' * 44)


class MvpFlowTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.storage = Path(temp.name)
        for mock in [patch.object(settings, 'document_storage_path', str(self.storage)),
                     patch('socket.socket.connect', side_effect=AssertionError('rede proibida'))]:
            mock.start()
            self.addCleanup(mock.stop)
        self.created = []

    def create(self, resource, id_field, **payload):
        response = self.client.post('/api/v1/' + resource, json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        entity = response.json()
        self.created.append((resource, id_field, entity))
        return entity

    def get(self, resource, entity_id):
        response = self.client.get(f'/api/v1/{resource}/{entity_id}')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def account(self):
        locality = self.create('localidades', 'id_localidade', codigo_localidade='DEMO-REC',
                               estado='PE', municipio='Recife', regiao='Nordeste')
        prefix = self.create('prefixos', 'id_prefixo', codigo_prefixo='DEMO',
                             nome='Unidade fictícia Recife', tipo_prefixo='agencia',
                             situacao='ativo', id_localidade=locality['id_localidade'])
        utility = self.create('concessionarias', 'id_concessionaria', cnpj='00000000000000',
                              razao_social='Energia Fictícia Demonstração', tipo_servico='energia')
        return self.create('contas_consumo', 'id_conta', numero_conta='DEMO-SEM-VALIDADE',
                           competencia='2026-10', data_vencimento='2026-10-20', valor_original='123.45',
                           categoria='energia', situacao='pendente', id_prefixo=prefix['id_prefixo'],
                           id_concessionaria=utility['id_concessionaria'])

    def upload_process(self, account, content):
        response = self.client.post(f"/api/v1/contas_consumo/{account['id_conta']}/documentos/upload",
                                   files={'file': ('demonstracao-ficticia.pdf', content, 'application/pdf')})
        self.assertEqual(response.status_code, 201, response.text)
        document = response.json()
        self.assertEqual(document['id_conta'], account['id_conta'])
        self.assertEqual((self.storage / document['caminho_arquivo']).read_bytes(), content)
        response = self.client.post(f"/api/v1/documentos/{document['id_documento']}/processar")
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['documento'], document)
        self.assertEqual(result['extracao']['id_documento'], document['id_documento'])
        self.assertEqual(result['situacao'], 'requer_validacao')
        return result

    def test_complete_mvp_flow(self):
        account = self.account()
        with patch('pytesseract.image_to_string') as ocr:
            result = self.upload_process(account, pdf(DEMO_TEXT))
        ocr.assert_not_called()
        fields = {f['campo_identificado']: f for f in result['campos_encontrados']}
        expected = dict(competencia='2026-10', data_vencimento='2026-10-20', valor_original='123.45',
                        consumo='100.500', codigo_barras='0' * 44)
        self.assertEqual({name: f['valor_extraido'] for name, f in fields.items()}, expected)
        self.assertEqual(Decimal(result['confianca_geral']), Decimal('95.00'))
        validated = {}
        for name, field in fields.items():
            self.assertEqual(field['id_extracao'], result['extracao']['id_extracao'])
            self.assertEqual(Decimal(field['nivel_confianca']), Decimal('95.00'))
            self.assertEqual(field['situacao_validacao'], 'pendente')
            self.assertIsNone(field['valor_validado'])
            # Ação humana explícita: corrige o valor e confirma os demais campos.
            response = self.client.patch(f"/api/v1/dados_extraidos/{field['id_dado_extraido']}/validacao",
                                         json={'valor_validado': '130.00'} if name == 'valor_original' else {})
            self.assertEqual(response.status_code, 200, response.text)
            validated[name] = response.json()
            self.assertEqual(validated[name], {**field, 'situacao_validacao': 'validada',
                                              'valor_validado': '130.00' if name == 'valor_original' else expected[name]})
        value = validated['valor_original']['valor_validado']
        self.assertEqual(self.get('contas_consumo', account['id_conta']), account)
        repeated = self.client.post(f"/api/v1/documentos/{result['documento']['id_documento']}/processar")
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(repeated.json()['extracao'], result['extracao'])
        self.assertEqual({f['campo_identificado']: f for f in repeated.json()['campos_encontrados']}, validated)
        rule = self.create('regras_calculo', 'id_regra', nome_regra='DEMO sem acréscimos', categoria='energia',
                           versao='demo-1', data_inicio_vigencia='2026-10-01', situacao='ativa')
        calculation = self.create('calculos', 'id_calculo', data_calculo='2026-10-06T12:00:00',
                                  valor_inicial=value, valor_calculado=value, situacao='validado',
                                  id_conta=account['id_conta'], id_regra=rule['id_regra'])
        system = self.create('sistemas_pagamento', 'id_sistema', nome='DEMO local fictício',
                             descricao='Somente cadastro; sem envio de pagamento', situacao='ativo')
        limits = [self.create('alcadas', 'id_alcada', nome_nivel=f'DEMO {limit}', limite_financeiro=limit,
                             data_inicio_vigencia='2026-10-01') for limit in ('1000.00', '129.99')]
        users = [self.create('usuarios', 'id_usuario', matricula=f'DEMO-{role}', nome=f'Pessoa fictícia {role}',
                             funcao=role, situacao='ativo', id_prefixo=account['id_prefixo'], id_alcada=limit['id_alcada'])
                 for role, limit in [('maker', limits[0]), ('checker', limits[0]), ('limite-baixo', limits[1])]]
        order = self.create('ordens_pagamento', 'id_ordem', data_criacao='2026-10-06T13:00:00',
                            data_prevista_pagamento='2026-10-20', valor_total=value, situacao='pendente',
                            id_calculo=calculation['id_calculo'], id_sistema=system['id_sistema'],
                            id_usuario_criador=users[0]['id_usuario'])
        item = self.create('itens_pagamento', 'id_item_pagamento', codigo_evento='DEMO',
                           descricao_evento='Energia fictícia', valor=value, id_ordem=order['id_ordem'])
        self.assertEqual(item['id_ordem'], order['id_ordem'])
        self.assertEqual(Decimal(order['valor_total']), Decimal(calculation['valor_calculado']))
        self.assertEqual(Decimal(item['valor']), Decimal(order['valor_total']))
        decision = dict(data_hora='2026-10-06T14:00:00', decisao='aprovado',
                        observacao='Decisão humana fictícia', id_ordem=order['id_ordem'])
        for user, status in [(users[0], 409), (users[2], 403)]:
            response = self.client.post('/api/v1/aprovacoes', json={**decision, 'id_usuario': user['id_usuario']})
            self.assertEqual(response.status_code, status, response.text)
            self.assertEqual(self.client.get('/api/v1/aprovacoes').json(), [])
            self.assertEqual(self.get('ordens_pagamento', order['id_ordem']), order)
        approval = self.create('aprovacoes', 'id_aprovacao', **decision, id_usuario=users[1]['id_usuario'])
        self.assertEqual(approval['id_ordem'], order['id_ordem'])
        self.assertEqual(approval['id_usuario'], users[1]['id_usuario'])
        order['situacao'] = 'aprovada'
        # Novas sessões HTTP verificam persistência e vínculos de todos os recursos.
        self.created.extend([('documentos', 'id_documento', result['documento']),
                             ('extracoes_inteligentes', 'id_extracao', result['extracao']),
                             *[('dados_extraidos', 'id_dado_extraido', f) for f in validated.values()]])
        for resource, id_field, entity in self.created:
            self.assertEqual(self.get(resource, entity[id_field]), entity)
        for resource, count in [('documentos', 1), ('extracoes_inteligentes', 1), ('dados_extraidos', 5),
                                ('calculos', 1), ('ordens_pagamento', 1), ('itens_pagamento', 1), ('aprovacoes', 1)]:
            response = self.client.get('/api/v1/' + resource)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()), count)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text('PRAGMA foreign_key_check')).all(), [])

    def test_pdf_without_text_uses_ocr_via_api(self):
        account = self.account()
        # Leitura/renderização reais; reconhecimento simulado para manter velocidade.
        with patch('pytesseract.get_languages', return_value=['por']), \
             patch('pytesseract.image_to_string', return_value=DEMO_TEXT) as ocr:
            result = self.upload_process(account, pdf())
        ocr.assert_called_once()
        self.assertEqual(len(result['campos_encontrados']), 5)
        self.assertEqual(Decimal(result['confianca_geral']), Decimal('80.00'))
        for field in result['campos_encontrados']:
            self.assertEqual(Decimal(field['nivel_confianca']), Decimal('80.00'))
            self.assertEqual(self.get('dados_extraidos', field['id_dado_extraido']), field)


if __name__ == '__main__':
    unittest.main()
