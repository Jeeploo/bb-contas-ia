"""Jornada persistida pela API, motor financeiro e Checker sem IA externa."""
import unittest
from unittest.mock import patch
from tests import test_documento_inicial as fixture


class JornadaDemoTests(unittest.TestCase):
    def setUp(self):
        fixture.DocumentoInicialTests.setUp(self)
        from app.core.config import settings
        mode = patch.object(settings, 'demo_mode', False)
        mode.start()
        self.addCleanup(mode.stop)
    restore_overrides = fixture.DocumentoInicialTests.restore_overrides
    upload = fixture.DocumentoInicialTests.upload
    configure = fixture.DocumentoInicialTests.configure
    processar = fixture.DocumentoInicialTests.processar

    def req(self, method, path, expected=200, **kwargs):
        response = getattr(self.client, method)('/api/v1/' + path, **kwargs)
        self.assertEqual(response.status_code, expected, response.text)
        return response.json() if response.content else None

    def read(self, **changes):
        self.configure(**{**dict(concessionaria='COMPANHIA ENERGÉTICA DE PERNAMBUCO', unidade_consumidora='999'), **changes})
        r = self.processar(self.upload())
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def confirm(self, r):
        for f in r['campos_encontrados']:
            self.req('patch', f"dados_extraidos/{f['id_dado_extraido']}/validacao", json={})
        for i in r['itens_encontrados']:
            self.req('patch', f"itens_extraidos/{i['id_item_extraido']}/validacao", json={})
        return self.req('post', f"extracoes_inteligentes/{r['extracao']['id_extracao']}/enviar-validacao", params={'id_usuario':1})

    def profile(self, estrategia='VALOR_INTEGRAL', parametros=None):
        rule=self.req('post','regras_calculo',201,json=dict(nome_regra='Regra vigente',categoria='energia',versao='1',data_inicio_vigencia='2026-01-01',situacao='ativa'))
        self.req('post','perfis_processamento',201,json=dict(id_prefixo=1,id_regra=rule['id_regra'],id_concessionaria=1,tipo_servico='energia',estrategia=estrategia,parametros=parametros or {},situacao='ativo',data_inicio_vigencia='2026-01-01'))

    def resume(self, user=1):
        return self.req('get','documentos/jornada/atual',params={'id_usuario':user})

    def calculate(self, r, expected=200):
        return self.req('post',f"documentos/{r['documento']['id_documento']}/calcular-demo",expected,params={'id_usuario':1})

    def test_duas_pendencias_calculo_com_regras_e_checker(self):
        r=self.read(); e=self.confirm(r)
        self.assertTrue(e['permite_envio_validacao']); self.assertFalse(e['bloqueia_calculo'])
        self.assertEqual({p['tipo'] for p in e['pendencias']},{'CORRESPONDENCIA_CONCESSIONARIA','VINCULO_UNIDADE'})
        self.assertIsNone(r['documento']['id_conta'])
        self.profile('COEFICIENTE',{'coeficiente':'1.1'})
        c=self.calculate(r)
        self.assertEqual(c['valor_inicial'],'736.53'); self.assertEqual(c['valor_calculado'],'669.57')
        self.assertEqual(c['memoria_calculo']['parametros']['coeficiente'],'1.1')
        self.assertFalse(c['memoria_calculo']['correspondencia_cadastral_confirmada'])
        self.assertEqual(self.calculate(r),c)
        self.assertEqual(self.resume()['calculo'],c)
        self.assertEqual(self.resume()['processamento']['extracao']['situacao_validacao'],'processamento_concluido')
        self.assertEqual(len(self.req('get','documentos/jornada/checker',params={'id_usuario':1})),1)
        self.provider.interpretar_documento.assert_called_once()

    def test_retomada_resumo_etapa3_conclusao_sem_ia(self):
        r=self.read()
        with patch('app.services.leitura_inteligente.get_document_ai_provider',side_effect=AssertionError('IA proibida')):
            restored=self.resume()
            self.assertEqual(restored['processamento'],r)
            self.req('get','contas_consumo')
            self.assertEqual(self.resume(),restored)
            sent=self.confirm(r)
            self.assertEqual(self.resume()['processamento']['extracao'],sent)
            self.assertIsNone(self.resume()['calculo'])
            self.profile(); c=self.calculate(r)
            self.assertEqual(self.resume()['calculo'],c)
        self.provider.interpretar_documento.assert_called_once()

    def test_nova_fatura_preserva_dados_sem_reviver_jornada_antiga(self):
        old=self.read(); new=self.read()
        self.assertEqual(self.resume()['documento']['id_documento'],new['documento']['id_documento'])
        self.req('post',f"documentos/{new['documento']['id_documento']}/nova-fatura",204,params={'id_usuario':1})
        self.assertIsNone(self.resume()['processamento'])
        for r in (old,new): self.req('get',f"documentos/{r['documento']['id_documento']}")
        id=self.upload()
        self.assertEqual(self.resume()['documento']['id_documento'],id)
        self.assertIsNone(self.resume()['processamento'])
        self.req('post',f'documentos/{id}/nova-fatura',204,params={'id_usuario':1})
        self.assertIsNone(self.resume()['documento'])

    def test_erros_reais_seguem_bloqueados(self):
        for changes in [dict(tipo_documento='OUTRO'),dict(uf='SP'),dict(valor_total=None),dict(competencia=None),dict(data_vencimento=None)]:
            with self.subTest(changes=changes):
                r=self.read(**changes)
                self.assertFalse(r['extracao']['permite_envio_validacao'])
                self.req('post',f"extracoes_inteligentes/{r['extracao']['id_extracao']}/enviar-validacao",403,params={'id_usuario':1})
                self.calculate(r,403)

    def test_regras_financeiras_nao_inventadas(self):
        r=self.read(); self.confirm(r)
        self.calculate(r,422); self.assertIsNone(self.resume()['calculo'])
        self.profile('COMPOSICAO_DETALHADA')
        self.calculate(r,422)
        self.assertEqual(self.req('get','documentos/jornada/checker',params={'id_usuario':1}),[])

    def test_checker_autoaprovacao_alcada_confirmacao_rejeicao(self):
        self.profile()
        self.req('post','alcadas',201,json=dict(nome_nivel='Checker',limite_financeiro='1000',data_inicio_vigencia='2026-01-01'))
        for matricula,alcada in [('C',1),('S',None)]:
            self.req('post','usuarios',201,json=dict(matricula=matricula,nome=matricula,funcao='checker',situacao='ativo',id_prefixo=1,id_alcada=alcada))
        r=self.read(); self.confirm(r); self.calculate(r)
        path=f"documentos/{r['documento']['id_documento']}/decisao-checker"
        self.req('post',path,409,params={'id_usuario':1},json={'decisao':'aprovado'})
        self.req('post',path,403,params={'id_usuario':3},json={'decisao':'aprovado'})
        result=self.req('post',path,params={'id_usuario':2},json={'decisao':'aprovado','observacao':'Conferido'})
        self.assertEqual(result['processamento']['extracao']['situacao_validacao'],'confirmada_checker')
        self.req('post',path,403,params={'id_usuario':2},json={'decisao':'rejeitado'})
        r=self.read(); self.confirm(r); self.calculate(r)
        result=self.req('post',f"documentos/{r['documento']['id_documento']}/decisao-checker",params={'id_usuario':2},json={'decisao':'rejeitado'})
        self.assertEqual(result['processamento']['extracao']['situacao_validacao'],'rejeitada_checker')

    def test_resumo_preserva_original_e_correcao(self):
        r=self.read(); f=next(f for f in r['campos_encontrados'] if f['campo_identificado']=='valor_original')
        self.req('patch',f"dados_extraidos/{f['id_dado_extraido']}/validacao",json={'valor_validado':'700.00'})
        saved=next(x for x in self.resume()['processamento']['campos_encontrados'] if x['id_dado_extraido']==f['id_dado_extraido'])
        self.assertEqual(saved['valor_extraido'],'736,53'); self.assertEqual(saved['valor_validado'],'700.00')

    def test_retomada_isolada_por_usuario_prefixo(self):
        self.read()
        self.req('post','usuarios',201,json=dict(matricula='Outro',nome='Outro',funcao='maker',situacao='ativo',id_prefixo=1))
        self.assertIsNone(self.resume(2)['documento'])
        self.req('get','documentos/jornada/atual',403,params={'id_usuario':1,'id_prefixo':99})

    def test_unidade_sem_vinculo_isolada_nao_bloqueia(self):
        r=self.read(concessionaria='Teste')
        e=self.confirm(r)
        self.assertEqual([p['tipo'] for p in e['pendencias']],['VINCULO_UNIDADE'])
        self.assertFalse(e['bloqueia_calculo']); self.profile(); self.calculate(r)

    def test_associacao_continua_opcional_apos_envio(self):
        r=self.read(); e=self.confirm(r)
        self.assertEqual(e['situacao_validacao'],'validada')
        e=self.req('post',f"extracoes_inteligentes/{e['id_extracao']}/resolver-concessionaria",params={'id_usuario':1},json={'id_concessionaria':1})
        self.assertFalse(e['bloqueia_calculo'])
        self.assertEqual(e['evidencias_validacao_documental']['origem_resolucao'],'manual')
        self.assertEqual([p['tipo'] for p in e['pendencias']],['VINCULO_UNIDADE'])

    def test_calculo_concluido_nao_pode_ser_alterado_silenciosamente(self):
        r=self.read(); self.confirm(r); self.profile(); self.calculate(r)
        f=r['campos_encontrados'][0]
        self.req('patch',f"dados_extraidos/{f['id_dado_extraido']}/validacao",403,json={'valor_validado':'OUTRO'})
        self.req('post',f"extracoes_inteligentes/{r['extracao']['id_extracao']}/enviar-validacao",403,params={'id_usuario':1})
        self.assertEqual(self.resume()['processamento']['extracao']['situacao_validacao'],'processamento_concluido')

    def test_retomada_atualiza_politica_legada_sem_ia(self):
        from sqlalchemy.orm import Session
        from app.models import ExtracaoInteligente
        r=self.read()
        with Session(self.engine) as session:
            e=session.get(ExtracaoInteligente,r['extracao']['id_extracao'])
            e.resultado_validacao_documental='EVIDENCIA_INSUFICIENTE'
            e.evidencias_validacao_documental={'versao_validador':2,'pendencias':[{'tipo':'CORRESPONDENCIA_CONCESSIONARIA','bloqueia_envio_validacao':False,'bloqueia_calculo':True}]}
            session.commit()
        with patch('app.services.leitura_inteligente.get_document_ai_provider',side_effect=AssertionError('IA proibida')):
            e=self.resume()['processamento']['extracao']
        self.assertFalse(e['bloqueia_calculo'])
        self.assertTrue(e['permite_envio_validacao'])
        self.assertEqual(e['evidencias_validacao_documental']['versao_validador'],3)
        self.provider.interpretar_documento.assert_called_once()

    def test_calculo_anterior_restaurado_pela_extracao_exata(self):
        r=self.read(concessionaria='Teste',unidade_consumidora='001'); self.confirm(r); self.profile()
        account=r['documento']['id_conta']
        legacy=self.req('post',f'contas_consumo/{account}/calcular',201)
        self.assertEqual(self.resume()['calculo'],legacy)

    def configure_coefficient_demo(self, result):
        from sqlalchemy.orm import Session
        from app.services.regra_demo import configurar_regra_demo
        with Session(self.engine) as session, session.begin():
            profile = configurar_regra_demo(session, result['documento']['id_documento'])
            return profile.id_perfil

    def test_coeficiente_demo_divide_com_decimal_e_arredonda(self):
        from decimal import Decimal, localcontext
        from app.calculation.strategies import CoefficientStrategy
        with localcontext() as ctx:
            ctx.prec=40
            expected=Decimal('736.53') / Decimal('0.9055')
        memory=CoefficientStrategy().execute(Decimal('736.53'),{'coeficiente':'0.9055'},[],[])
        self.assertEqual(memory['resultado_sem_arredondamento'],str(expected))
        self.assertEqual(memory['resultado'],'813.40')
        self.assertEqual(memory['diferenca'],'76.87')
        self.assertEqual(memory['operacao'],'DIVISAO')
        self.assertEqual(memory['expressao'],'736.53 / 0.9055')

    def test_coeficiente_demo_persistido_memoria_retomada_checker_sem_ia(self):
        from app.services.regra_demo import AVISO_DEMO, NOME_REGRA
        r=self.read(); self.confirm(r)
        pid=self.configure_coefficient_demo(r)
        profile=self.req('get',f'perfis_processamento/{pid}')
        self.assertEqual(profile['parametros']['coeficiente'],'0.9055')
        self.assertEqual(profile['parametros']['escopo_demo'],{'id_prefixo':1,'competencia':'2026-09'})
        self.assertEqual(profile['data_fim_vigencia'],'2026-09-30')
        with patch('app.services.leitura_inteligente.get_document_ai_provider',side_effect=AssertionError('Nova IA proibida')):
            calculation=self.calculate(r)
            self.assertEqual(calculation['valor_calculado'],'813.40')
            memory=calculation['memoria_calculo']
            self.assertEqual(memory['nome_regra'],NOME_REGRA)
            self.assertEqual(memory['aviso_demo'],AVISO_DEMO)
            self.assertTrue(memory['demonstrativa'])
            self.assertEqual(memory['coeficiente'],'0.9055')
            self.assertEqual(memory['expressao'],'736.53 / 0.9055')
            self.assertEqual(memory['diferenca'],'76.87')
            self.assertEqual(self.resume()['calculo'],calculation)
            self.assertEqual(self.calculate(r),calculation)
            queue=self.req('get','documentos/jornada/checker',params={'id_usuario':1})
            self.assertEqual(queue[0]['calculo'],calculation)
            self.req('post','alcadas',201,json=dict(nome_nivel='Checker',limite_financeiro='813.40',data_inicio_vigencia='2026-01-01'))
            self.req('post','usuarios',201,json=dict(matricula='C',nome='Checker',funcao='checker',situacao='ativo',id_prefixo=1,id_alcada=1))
            path=f"documentos/{r['documento']['id_documento']}/decisao-checker"
            self.req('post',path,409,params={'id_usuario':1},json={'decisao':'aprovado'})
            decision=self.req('post',path,params={'id_usuario':2},json={'decisao':'aprovado'})
            self.assertEqual(decision['calculo'],calculation)
            self.assertEqual(decision['processamento']['extracao']['situacao_validacao'],'confirmada_checker')
        self.provider.interpretar_documento.assert_called_once()

    def test_configuracao_demo_idempotente_preserva_outros_prefixos(self):
        self.req('post','prefixos',201,json=dict(codigo_prefixo='OUTRO',nome='Outro',tipo_prefixo='agencia',situacao='ativo',id_localidade=1))
        rule=self.req('post','regras_calculo',201,json=dict(nome_regra='Regra existente',categoria='energia',versao='1',data_inicio_vigencia='2026-01-01',situacao='ativa'))
        other=self.req('post','perfis_processamento',201,json=dict(id_prefixo=2,id_regra=rule['id_regra'],tipo_servico='energia',estrategia='VALOR_INTEGRAL',parametros={},situacao='ativo',data_inicio_vigencia='2026-01-01'))
        r=self.read()
        self.assertEqual(self.configure_coefficient_demo(r),self.configure_coefficient_demo(r))
        self.assertEqual(self.req('get',f"perfis_processamento/{other['id_perfil']}"),other)
        self.assertEqual(self.req('get',f"regras_calculo/{rule['id_regra']}"),rule)
        self.assertEqual(len(self.req('get','perfis_processamento')),2)
        self.assertEqual(len(self.req('get','regras_calculo')),2)

    def test_demo_nao_sobrescreve_perfil_existente(self):
        from app.services.exceptions import CalculationError
        self.profile()
        before=self.req('get','perfis_processamento')
        r=self.read()
        with self.assertRaises(CalculationError): self.configure_coefficient_demo(r)
        self.assertEqual(self.req('get','perfis_processamento'),before)
        self.assertEqual(len(self.req('get','regras_calculo')),1)

    def test_regra_demo_nao_pode_ser_generalizada_para_outro_escopo(self):
        from sqlalchemy.orm import Session
        from app.models import PerfilProcessamento
        r=self.read(); self.confirm(r); pid=self.configure_coefficient_demo(r)
        with Session(self.engine) as session, session.begin():
            profile=session.get(PerfilProcessamento,pid)
            profile.parametros={**profile.parametros,'escopo_demo':dict(id_prefixo=2,competencia='2026-09')}
        self.calculate(r,422)
        self.assertIsNone(self.resume()['calculo'])

    def test_fallback_demo_sem_configuracao_memoria_retomada_sem_ia(self):
        from app.core.config import settings
        for _ in range(2):
            r = self.read(); self.confirm(r)
            with patch.object(settings, 'demo_mode', True), patch(
                'app.services.leitura_inteligente.get_document_ai_provider', side_effect=AssertionError('IA proibida')):
                c = self.calculate(r)
                self.assertEqual(c['valor_calculado'], '813.40')
                m = c['memoria_calculo']
                self.assertEqual(m['valor_original'], '736.53')
                self.assertEqual(m['diferenca'], '76.87')
                self.assertEqual(m['coeficiente'], '0.9055')
                self.assertEqual(m['arredondamento'], 'ROUND_HALF_UP')
                self.assertTrue(m['fallback_demo'])
                with patch('app.services.calculo_contextual.CalculoContextualService.executar', side_effect=AssertionError('Recalculo proibido')), patch(
                    'app.services.validacao_documental.ValidacaoDocumentalService.revalidar', side_effect=AssertionError('Revalidacao proibida')):
                    self.assertEqual(self.resume()['calculo'], c)
                    self.assertEqual(self.calculate(r), c)
        self.assertEqual(self.req('get', 'perfis_processamento'), [])
        self.assertEqual(self.req('get', 'regras_calculo'), [])

    def test_fallback_demo_configuracao_incompleta_e_perfis_ambiguos(self):
        from app.core.config import settings
        from sqlalchemy.orm import Session
        from app.models import PerfilProcessamento
        self.profile('COEFICIENTE', {'coeficiente': '1.1'})
        with Session(self.engine) as session, session.begin():
            session.get(PerfilProcessamento, 1).parametros = {}
        r = self.read(); self.confirm(r)
        with patch.object(settings, 'demo_mode', False):
            self.calculate(r, 422)
        with patch.object(settings, 'demo_mode', True):
            self.assertEqual(self.calculate(r)['valor_calculado'], '813.40')
        # A API impede sobreposição; simula configuração legada inconsistente no banco isolado.
        with Session(self.engine) as session, session.begin():
            profile = session.get(PerfilProcessamento, 1)
            session.add(PerfilProcessamento(id_prefixo=profile.id_prefixo, id_regra=profile.id_regra,
                tipo_servico=profile.tipo_servico, estrategia='VALOR_INTEGRAL', parametros={},
                situacao='ativo', data_inicio_vigencia=profile.data_inicio_vigencia))
        r = self.read(); self.confirm(r)
        with patch.object(settings, 'demo_mode', True):
            self.assertTrue(self.calculate(r)['memoria_calculo']['fallback_demo'])

    def test_demo_preserva_perfil_valido_e_fora_demo_bloqueia(self):
        from app.core.config import settings
        r = self.read(); self.confirm(r)
        with patch.object(settings, 'demo_mode', False):
            self.calculate(r, 422)
        self.profile('COEFICIENTE', {'coeficiente': '1.1'})
        with patch.object(settings, 'demo_mode', True):
            self.assertEqual(self.calculate(r)['valor_calculado'], '669.57')

    def test_confirmacao_agregada_revalida_uma_vez_e_retorna_etapa3(self):
        from app.services.validacao_documental import ValidacaoDocumentalService
        r = self.read()
        original = ValidacaoDocumentalService.revalidar
        with patch.object(ValidacaoDocumentalService, 'revalidar', autospec=True, side_effect=original) as validation:
            j = self.req('post', f"documentos/{r['documento']['id_documento']}/confirmar-jornada",
                         params={'id_usuario': 1}, json={'valores': {}, 'enviar': True})
            self.assertEqual(validation.call_count, 1)
        self.assertEqual(j['processamento']['extracao']['situacao_validacao'], 'validada')
        self.assertTrue(all(f['situacao_validacao'] == 'validada' for f in j['processamento']['campos_encontrados']))
        self.assertIsNone(j['calculo'])
        self.provider.interpretar_documento.assert_called_once()

    def test_confirmacao_agregada_rollback_campo_invalido(self):
        r = self.read()
        field = next(f for f in r['campos_encontrados'] if f['campo_identificado'] == 'competencia')
        self.req('post', f"documentos/{r['documento']['id_documento']}/confirmar-jornada", 422,
                 params={'id_usuario': 1}, json={'valores': {'d' + str(field['id_dado_extraido']): 'invalida'}})
        self.assertTrue(all(f['situacao_validacao'] != 'validada' for f in self.resume()['processamento']['campos_encontrados']))
