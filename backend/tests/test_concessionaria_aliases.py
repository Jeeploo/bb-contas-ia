"""Resolução cadastral com evidências persistidas; sem IA, rede ou cálculo."""
import unittest
from unittest.mock import patch
from sqlalchemy import select, func
from app import models
from app.services.correspondencia_concessionaria import normalizar_nome, correspondencias, associar
from app.services.validacao_documental import ValidacaoDocumentalService, politica_revisao
from app.services.exceptions import ContextoOperacionalError
from app.schemas.leitura_documental import ContextoDocumental
from tests import test_validacao_documental as fixture


class AliasTests(unittest.TestCase):
    setUp = fixture.ValidacaoDocumentalTests.setUp
    registrar = fixture.ValidacaoDocumentalTests.registrar
    nome = 'COMPANHIA ENERGÉTICA DE PERNAMBUCO'

    def alias(self, cid=1, ativo=True):
        self.s.add(models.ConcessionariaAlias(id_concessionaria=cid, alias=self.nome,
            alias_normalizado=normalizar_nome(self.nome), ativo=ativo))
        self.s.flush()

    def extraction(self, **changes):
        e = self.registrar(concessionaria=self.nome, competencia='2026-10',
            data_vencimento='2026-10-20', valor_total=100, **changes)
        for field in e.dados_extraidos:
            field.valor_validado = field.valor_normalizado or field.valor_extraido
            field.situacao_validacao = 'validada'
        e.situacao_validacao = 'revisao_cadastral_pendente'
        self.s.flush()
        return e

    def associate(self, e, cid=1):
        return associar(self.s, e, cid, ContextoDocumental(id_usuario=1,id_prefixo=1))

    def test_normalizacao(self):
        self.assertEqual(normalizar_nome('  Companhia Energética  de Pernambuco S.A. '), 'COMPANHIA ENERGETICA DE PERNAMBUCO SA')
        self.assertNotEqual(normalizar_nome('Empresa A'), normalizar_nome('Empresa B'))

    def test_alias_automatico_auditado(self):
        self.alias()
        e = self.extraction()
        self.assertEqual(e.resultado_validacao_documental, 'VALIDO')
        self.assertEqual(e.evidencias_validacao_documental['id_concessionaria'], 1)
        self.assertEqual(e.evidencias_validacao_documental['origem_correspondencia'], 'alias')
        self.assertEqual(e.historico_validacao_documental[-1]['evidencias']['origem_resolucao'], 'automatica')

    def test_ambiguidade(self):
        self.alias(); self.alias(2)
        e = self.extraction()
        self.assertNotIn('id_concessionaria', e.evidencias_validacao_documental)
        self.assertTrue(politica_revisao(e)['bloqueia_calculo'])

    def test_nome_oficial_e_alias_conflitantes(self):
        self.s.get(models.Concessionaria, 2).razao_social = self.nome
        self.alias()
        self.assertEqual(len(correspondencias(self.s, self.nome)[0]), 2)

    def test_alias_inativo(self):
        self.alias(ativo=False)
        self.assertEqual(correspondencias(self.s, self.nome)[0], [])

    def test_concessionaria_inativa(self):
        self.alias(); self.s.get(models.Concessionaria,1).ativo=False; self.s.flush()
        self.assertEqual(correspondencias(self.s, self.nome)[0], [])
        with self.assertRaises(ContextoOperacionalError): self.associate(self.extraction())

    def test_inexistente(self):
        with self.assertRaises(ContextoOperacionalError): self.associate(self.extraction(),999)
        self.assertEqual(self.s.scalar(select(func.count()).select_from(models.ConcessionariaAlias)),0)

    def test_manual_preserva_nome_salva_id_alias_auditoria_sem_ia(self):
        e = self.extraction()
        with patch('app.services.leitura_inteligente.get_document_ai_provider', side_effect=AssertionError('IA proibida')):
            self.associate(e)
        self.assertFalse(politica_revisao(e)['bloqueia_calculo'])
        self.assertEqual(e.situacao_validacao,'validada')
        self.assertEqual(e.evidencias_validacao_documental['id_concessionaria'],1)
        self.assertEqual(next(f.valor_extraido for f in e.dados_extraidos if f.campo_identificado=='concessionaria'),self.nome)
        audit = next(h for h in e.historico_validacao_documental if h.get('evento')=='CONCESSIONARIA_ASSOCIADA')
        for key, value in dict(id_usuario=1,id_concessionaria=1,nome_extraido=self.nome,id_documento=1,id_extracao=e.id_extracao,origem='manual').items():
            self.assertEqual(audit[key],value)
        self.assertIn('data', audit)
        self.assertEqual(self.s.scalar(select(func.count()).select_from(models.Concessionaria)),2)
        self.assertEqual(self.s.scalar(select(models.ConcessionariaAlias)).alias,self.nome)
        self.assertEqual(self.s.scalar(select(func.count()).select_from(models.Calculo)),0)

    def test_alias_duplicado_nao_criado(self):
        e = self.extraction(); self.alias(); self.associate(e)
        self.assertEqual(self.s.scalar(select(func.count()).select_from(models.ConcessionariaAlias)),1)

    def test_outra_pendencia_bloqueia_calculo(self):
        e = self.extraction(unidade_consumidora='999')
        self.associate(e)
        self.assertTrue(politica_revisao(e)['bloqueia_calculo'])
        self.assertEqual(e.situacao_validacao,'revisao_cadastral_pendente')

    def test_manual_resolve_ambiguidade_apenas_neste_documento(self):
        self.alias(); self.alias(2)
        e = self.extraction(); self.associate(e)
        ValidacaoDocumentalService(self.s).revalidar(e)
        self.assertEqual(e.evidencias_validacao_documental['id_concessionaria'],1)
        other = self.extraction()
        self.assertNotIn('id_concessionaria',other.evidencias_validacao_documental)

    def test_nome_alterado_invalida_decisao_manual(self):
        e=self.extraction(); self.associate(e)
        field=next(f for f in e.dados_extraidos if f.campo_identificado=='concessionaria')
        field.valor_validado='Outra empresa'
        ValidacaoDocumentalService(self.s).revalidar(e)
        self.assertNotIn('id_concessionaria',e.evidencias_validacao_documental)
