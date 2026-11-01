"""Fixtures técnicas fictícias; nenhum dado pessoal."""
from decimal import Decimal as D
import unittest
from app.calculation.strategies import (IntegralValueStrategy, CoefficientStrategy,
    DetailedCompositionStrategy, Component, validate_parameters)
from app.services.exceptions import CalculationError
from app.processing.structured import DeterministicStructuredExtractor
from tests import test_mvp_flow
from tests.test_processamento_documento import pdf

LAYOUT_A = '''Competência: 09/2026
Vencimento: 20/10/2026
Valor total: R$ 736,53
Consumo: 523 kWh
Consumo-TUSD | 523 kWh | 0,72428200 | 378,79
Consumo-TE: 186,60
Bandeira amarela: 13,32
Iluminação pública: 65,47
PIS: 5,75
COFINS: 26,68
ICMS | 659,05 | 18,00% | 118,63
'''
LAYOUT_B = '''ICMS: 118,63
COFINS  26,68
ENERGIA (TE) 186,60
Total a pagar
R$ 736,53
Iluminação pública | 65,47
Vencimento | 20/10/2026
PIS: 5,75
USO SIST. DISTR. (TUSD): 378,79
Consumo | 523 kWh
Bandeira amarela 13,32
Competência
09/2026
'''


class StrategyTests(unittest.TestCase):
    def test_integral(self):
        self.assertEqual(IntegralValueStrategy().execute(D('736.53'), {}, [], [])['resultado'], '736.53')

    def test_coefficient(self):
        for coefficient, expected in [('2', '5000.00'), ('0.85', '11764.71')]:
            result = CoefficientStrategy().execute(D('10000'), {'coeficiente': coefficient}, [], [])
            self.assertEqual(result['resultado'], expected)
            self.assertEqual(result['arredondamento'], 'ROUND_HALF_UP')

    def test_round_half_up(self):
        self.assertEqual(CoefficientStrategy().execute(D('1.01'), {'coeficiente': '2'}, [], [])['resultado'], '0.51')

    def test_invalid_coefficient(self):
        for params in [{}, {'coeficiente': '0'}, {'coeficiente': '-1'}, {'coeficiente': 'NaN'}, {'coeficiente': 'Infinity'}]:
            with self.subTest(params=params), self.assertRaises(CalculationError):
                validate_parameters('COEFICIENTE', params)

    def test_composition_memory_discount_optional_ignored(self):
        components = [Component(1, 'TUSD', D('378.79'), True), Component(2, 'TE', D('186.60'), True),
                      Component(3, 'DESCONTO', D('10'), True), Component(4, 'ICMS', D('118.63'), False)]
        rules = [dict(tipo=k, operacao=o, obrigatorio=r) for k,o,r in
                 [('TUSD','SOMAR',True), ('TE','SOMAR',True), ('DESCONTO','DESCONTO',True), ('PIS','SOMAR',False)]]
        memory = DetailedCompositionStrategy().execute(D('736.53'), {}, components, rules)
        self.assertEqual(memory['resultado'], '555.39')
        self.assertEqual(len(memory['componentes_considerados']), 3)
        self.assertEqual(memory['componentes_ignorados'][0]['tipo'], 'ICMS')

    def test_composition_missing_required(self):
        with self.assertRaisesRegex(CalculationError, 'ausente'):
            DetailedCompositionStrategy().execute(D(0), {}, [], [dict(tipo='TE', operacao='SOMAR')])

    def test_composition_unvalidated(self):
        with self.assertRaisesRegex(CalculationError, 'não validado'):
            DetailedCompositionStrategy().execute(D(0), {}, [Component(1,'TE',D(10),False)], [dict(tipo='TE',operacao='SOMAR')])

    def test_composition_invalid_rule(self):
        for rules in [[], [dict(tipo='TE', operacao='INVALIDA')], [dict(tipo='TE', operacao='SOMAR', obrigatorio=False)] * 2]:
            with self.assertRaises(CalculationError):
                DetailedCompositionStrategy().execute(D(0), {}, [], rules)


class ExtractionTests(unittest.TestCase):
    def test_two_layouts(self):
        results = [DeterministicStructuredExtractor().extract(text, {}) for text in (LAYOUT_A, LAYOUT_B)]
        for result in results:
            self.assertEqual({f.campo_identificado:f.valor_extraido for f in result.campos},
                             dict(competencia='2026-09',data_vencimento='2026-10-20',valor_original='736.53',consumo='523'))
            self.assertEqual({i.tipo_normalizado:i.valor for i in result.itens},
                             dict(TUSD=D('378.79'),TE=D('186.60'),BANDEIRA=D('13.32'),
                                  ILUMINACAO_PUBLICA=D('65.47'),PIS=D('5.75'),COFINS=D('26.68'),ICMS=D('118.63')))
        tusd = results[0].itens[0]
        self.assertEqual(tusd.quantidade,D(523))
        self.assertEqual(tusd.valor_unitario,D('0.72428200'))
        tax = results[0].itens[-1]
        self.assertEqual(tax.base_calculo,D('659.05'))
        self.assertEqual(tax.aliquota,D('18'))

    def test_extensible_alias(self):
        result = DeterministicStructuredExtractor({'AGUA':['Consumo água']}).extract('Consumo água: 25,00', {})
        self.assertEqual(result.itens[0].tipo_normalizado, 'AGUA')

    def test_unknown_and_malformed_not_inferred(self):
        result = DeterministicStructuredExtractor().extract('XYZ: 20,00\nTUSD: inválido\nTE: 1,00 ou 2,00', {})
        self.assertEqual(result.itens, [])


class ContextTests(test_mvp_flow.MvpFlowTests):
    # Herdar somente os helpers, evitando repetir os testes do MVP.
    test_complete_mvp_flow = None
    test_pdf_without_text_uses_ocr_via_api = None

    def setup_context(self, strategy='VALOR_INTEGRAL', **changes):
        account = self.account()
        result = self.upload_process(account, pdf(LAYOUT_A))
        for field in result['campos_encontrados']:
            response = self.client.patch(f"/api/v1/dados_extraidos/{field['id_dado_extraido']}/validacao", json={})
            self.assertEqual(response.status_code, 200)
        rule = self.create('regras_calculo','id_regra',nome_regra='Fixture',categoria='energia',versao='1',
                           situacao='ativa',data_inicio_vigencia='2026-01-01')
        config = dict(id_prefixo=account['id_prefixo'],tipo_servico='energia',estrategia=strategy,
                      id_regra=rule['id_regra'],situacao='ativo',data_inicio_vigencia='2026-01-01',
                      parametros={'coeficiente':'0.85'} if strategy=='COEFICIENTE' else {})
        config.update(changes)
        profile = self.create('perfis_processamento','id_perfil',**config)
        return account,result,rule,profile

    def calculate(self, account):
        return self.client.post(f"/api/v1/contas_consumo/{account['id_conta']}/calcular")

    def test_automatic_integral_and_persisted_memory(self):
        account,result,rule,profile=self.setup_context()
        response=self.calculate(account)
        self.assertEqual(response.status_code,201,response.text)
        calc=response.json()
        self.assertEqual(D(calc['valor_calculado']),D('736.53'))
        self.assertEqual(calc['memoria_calculo']['id_perfil'],profile['id_perfil'])
        self.assertEqual(self.get('calculos',calc['id_calculo']),calc)

    def test_automatic_coefficient(self):
        account,*_=self.setup_context('COEFICIENTE')
        response=self.calculate(account)
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(D(response.json()['valor_calculado']),D('866.51'))

    def test_automatic_composition_requires_validation_preserves_raw(self):
        account,result,rule,_=self.setup_context('COMPOSICAO_DETALHADA')
        for order,kind in enumerate(['TUSD','TE']):
            self.create('itens_regra','id_item_regra',nome_item=kind,tipo_item='SOMAR',ordem_aplicacao=order,id_regra=rule['id_regra'])
        self.assertEqual(self.calculate(account).status_code,422)
        for item in result['itens_encontrados']:
            if item['tipo_normalizado'] not in ['TUSD','TE']: continue
            correction={'valor_validado':'380.00'} if item['tipo_normalizado']=='TUSD' else {}
            response=self.client.patch(f"/api/v1/itens_extraidos/{item['id_item_extraido']}/validacao",json=correction)
            self.assertEqual(response.status_code,200,response.text)
            validated=response.json()
            self.assertEqual(validated['valor'],item['valor'])
            self.assertEqual(validated['nivel_confianca'],item['nivel_confianca'])
            self.assertEqual(validated['descricao_original'],item['descricao_original'])
        response=self.calculate(account)
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(D(response.json()['valor_calculado']),D('566.60'))
        repeated=self.client.post(f"/api/v1/documentos/{result['documento']['id_documento']}/processar")
        self.assertEqual(len(repeated.json()['itens_encontrados']),7)
        self.assertEqual(len(self.client.get('/api/v1/itens_extraidos').json()),7)

    def test_missing_profile_extraction_still_works(self):
        account=self.account()
        result=self.upload_process(account,pdf(LAYOUT_A))
        for f in result['campos_encontrados']:
            self.client.patch(f"/api/v1/dados_extraidos/{f['id_dado_extraido']}/validacao",json={})
        response=self.calculate(account)
        self.assertEqual(response.status_code,422)
        self.assertIn('perfil',response.json()['detail'])
        self.assertEqual(self.client.get('/api/v1/calculos').json(),[])

    def test_inactive_rule(self):
        account,_,rule,_=self.setup_context()
        self.client.patch(f"/api/v1/regras_calculo/{rule['id_regra']}",json={'situacao':'inativa'})
        response=self.calculate(account)
        self.assertEqual(response.status_code,422)
        self.assertIn('inativa',response.json()['detail'])

    def test_invalid_rule_validity(self):
        account,_,rule,_=self.setup_context()
        self.client.patch(f"/api/v1/regras_calculo/{rule['id_regra']}",json={'data_inicio_vigencia':'2026-10-01'})
        self.assertEqual(self.calculate(account).status_code,422)

    def test_invalid_profile_validity(self):
        account,*_=self.setup_context(data_inicio_vigencia='2026-10-01')
        self.assertEqual(self.calculate(account).status_code,422)

    def test_unvalidated_total(self):
        account,result,*_=self.setup_context()
        total=next(f for f in result['campos_encontrados'] if f['campo_identificado']=='valor_original')
        self.client.patch(f"/api/v1/dados_extraidos/{total['id_dado_extraido']}",json={'situacao_validacao':'pendente'})
        self.assertEqual(self.calculate(account).status_code,422)

    def test_profile_overlap_and_invalid_patch(self):
        account,_,_,profile=self.setup_context()
        payload={k:v for k,v in profile.items() if k!='id_perfil'}
        response=self.client.post('/api/v1/perfis_processamento',json=payload)
        self.assertEqual(response.status_code,422,response.text)
        response=self.client.patch(f"/api/v1/perfis_processamento/{profile['id_perfil']}",json={'estrategia':'COEFICIENTE'})
        self.assertEqual(response.status_code,422,response.text)

    def test_component_null_correction_rejected(self):
        _,result,*_=self.setup_context()
        item=result['itens_encontrados'][0]
        response=self.client.patch(f"/api/v1/itens_extraidos/{item['id_item_extraido']}/validacao",json={'valor_validado':None})
        self.assertEqual(response.status_code,422)


class SeedTests(test_mvp_flow.ApiTestCase):
    def test_seed_idempotent_preserves_existing_demo_and_prepares_profiles(self):
        from scripts.seed_demo import prepare
        from contextlib import redirect_stdout
        from io import StringIO
        resources = ['localidades', 'prefixos', 'concessionarias', 'contas_consumo',
                     'regras_calculo', 'perfis_processamento', 'itens_regra',
                     'calculos', 'ordens_pagamento', 'usuarios', 'itens_pagamento',
                     'documentos', 'extracoes_inteligentes']
        with redirect_stdout(StringIO()):
            prepare(self.client, 'fixture')
            before = {r:self.client.get('/api/v1/'+r).json() for r in resources}
            prepare(self.client, 'fixture')
        after = {r:self.client.get('/api/v1/'+r).json() for r in resources}
        self.assertEqual(before, after)
        self.assertEqual(len(after['perfis_processamento']), 3)
        self.assertEqual({p['estrategia'] for p in after['perfis_processamento']},
                         {'COEFICIENTE', 'COMPOSICAO_DETALHADA', 'VALOR_INTEGRAL'})
        self.assertEqual(len(after['calculos']), 1)
        self.assertEqual(len(after['documentos']), 12)
        self.assertTrue(all(d['origem'] == 'DEMO estruturada sem IA' and d['formato'] == 'json'
                            for d in after['documentos']))
        self.assertEqual(len(after['extracoes_inteligentes']), 12)
