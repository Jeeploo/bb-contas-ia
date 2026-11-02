"""Validação e autorização com dados simulados, sem IA/OCR/rede."""
import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from app import models
from app.core.config import settings
from app.schemas.leitura_documental import LeituraDocumental, ContextoDocumental
from app.schemas.vinculos import UsuarioPrefixoEntrada as V, UnidadeConsumidoraCreate
from app.schemas.usuario import UsuarioCreate
from app.schemas.dado_extraido import DadoExtraidoValidacao, DadoExtraidoPatch
from app.services.usuario import UsuarioService
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.validacao_documental import ValidacaoDocumentalService
from app.services.interpretacao_documental import InterpretacaoDocumentalService
from app.services.dado_extraido import DadoExtraidoService
from app.services.exceptions import ContextoOperacionalError


class ValidacaoDocumentalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        @event.listens_for(self.engine, 'connect')
        def fk(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        models.Base.metadata.create_all(self.engine)
        self.s = Session(self.engine, autoflush=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.s.close)
        self.s.add(models.Localidade(id_localidade=1, codigo_localidade='L', estado='PE', municipio='Recife'))
        self.s.flush()
        for i in (1, 2):
            self.s.add(models.Prefixo(id_prefixo=i, codigo_prefixo=f'P{i}', nome='Unidade', tipo_prefixo='agencia', situacao='ativo', id_localidade=1))
            self.s.add(models.Concessionaria(id_concessionaria=i, cnpj=str(i)*14,
                razao_social=f'Empresa {i}', tipo_servico='energia' if i == 1 else 'agua'))
        self.s.commit()
        self.user = UsuarioService(self.s).create(UsuarioCreate(matricula='M', nome='Usuário', funcao='operador', situacao='ativo', id_prefixo=1))
        self.ctx = ContextoOperacionalService(self.s)
        for cid in (1, 2):
            self.ctx.cadastrar_unidade(UnidadeConsumidoraCreate(id_prefixo=1, id_concessionaria=cid, unidade_consumidora='001'))
            self.ctx.cadastrar_unidade(UnidadeConsumidoraCreate(id_prefixo=2, id_concessionaria=cid, unidade_consumidora='002'))
        self.s.add(models.ContaConsumo(id_conta=1, competencia='2026-10', data_vencimento=date(2026,10,20),
            valor_original=100, categoria='energia', situacao='pendente', id_prefixo=1, id_concessionaria=1))
        self.s.flush()
        self.s.add(models.Documento(id_documento=1, tipo_documento='fatura', formato='pdf',
            data_recebimento=datetime(2026,10,1), origem='teste', caminho_arquivo='x.pdf', id_conta=1))
        self.s.commit()
        self.dados = dict(tipo_documento='ENERGIA', uf='PE', municipio='Recife', concessionaria='Empresa 1', unidade_consumidora='001')

    def avaliar(self, **changes):
        return ValidacaoDocumentalService(self.s).avaliar({**self.dados, **changes}, 1, 1)[0]

    def registrar(self, **changes):
        return InterpretacaoDocumentalService(self.s).registrar(1, LeituraDocumental(**{**self.dados, **changes}), ContextoDocumental(id_usuario=1, id_prefixo=1))

    def test_energia_pe_valida(self):
        self.assertEqual(self.avaliar(), 'VALIDO')

    def test_agua_pe_valida(self):
        self.assertEqual(self.avaliar(tipo_documento='AGUA', concessionaria='Empresa 2'), 'VALIDO')

    def test_boleto(self):
        self.assertEqual(self.avaliar(tipo_documento='BOLETO'), 'DOCUMENTO_NAO_SUPORTADO')

    def test_comprovante(self):
        self.assertEqual(self.avaliar(tipo_documento='COMPROVANTE'), 'DOCUMENTO_NAO_SUPORTADO')

    def test_outros_documentos(self):
        for tipo in ('NOTA_FISCAL', 'DOCUMENTO_BANCARIO', 'OUTRO'):
            with self.subTest(tipo=tipo):
                self.assertEqual(self.avaliar(tipo_documento=tipo), 'DOCUMENTO_NAO_SUPORTADO')

    def test_energia_outra_uf(self):
        self.assertEqual(self.avaliar(uf='BA'), 'REGIAO_NAO_SUPORTADA')

    def test_agua_outra_uf(self):
        self.assertEqual(self.avaliar(tipo_documento='AGUA', uf='AL'), 'REGIAO_NAO_SUPORTADA')

    def test_tipo_ausente(self):
        self.assertEqual(self.avaliar(tipo_documento=None), 'EVIDENCIA_INSUFICIENTE')

    def test_uf_ausente(self):
        self.assertEqual(self.avaliar(uf=None), 'EVIDENCIA_INSUFICIENTE')

    def test_unidade_ausente(self):
        self.assertEqual(self.avaliar(unidade_consumidora=None), 'EVIDENCIA_INSUFICIENTE')

    def test_municipio_ausente(self):
        self.assertEqual(self.avaliar(municipio=None), 'EVIDENCIA_INSUFICIENTE')

    def test_concessionaria_ausente(self):
        self.assertEqual(self.avaliar(concessionaria=None), 'EVIDENCIA_INSUFICIENTE')

    def test_vinculo_desconhecido_nao_e_divergencia(self):
        self.assertEqual(self.avaliar(unidade_consumidora='999'), 'VALIDO')

    def test_um_prefixo_automatico(self):
        self.assertEqual(self.ctx.resolver(1).id_prefixo, 1)

    def test_multiplos_exigem_selecao(self):
        self.ctx.definir(1, [V(id_prefixo=1), V(id_prefixo=2)])
        with self.assertRaises(ContextoOperacionalError):
            self.ctx.resolver(1)
        self.assertEqual(self.ctx.resolver(1, 2).id_prefixo, 2)

    def test_sem_prefixo_ativo(self):
        with self.assertRaises(ContextoOperacionalError):
            self.ctx.definir(1, [V(id_prefixo=1, ativo=False)])
        self.assertEqual(self.ctx.resolver(1).id_prefixo, 1)

    def test_novo_operacional_sem_prefixo(self):
        with self.assertRaises(ContextoOperacionalError):
            UsuarioService(self.s).create(UsuarioCreate(matricula='N', nome='N', funcao='operador', situacao='ativo'))

    def test_prefixo_autorizado(self):
        self.assertEqual(self.ctx.resolver(1, 1).id_prefixo, 1)

    def test_prefixo_nao_autorizado(self):
        with self.assertRaises(ContextoOperacionalError):
            self.ctx.resolver(1, 2)

    def test_ingestao_nao_autorizada(self):
        with self.assertRaises(ContextoOperacionalError):
            InterpretacaoDocumentalService(self.s).registrar(1, LeituraDocumental(**self.dados), ContextoDocumental(id_usuario=1,id_prefixo=2))
        self.assertEqual(list(self.s.scalars(select(models.ExtracaoInteligente))), [])

    def test_unidade_outra_no_mesmo_municipio(self):
        self.assertEqual(self.avaliar(unidade_consumidora='002'), 'DIVERGENCIA_PREFIXO')

    def test_municipio_divergente(self):
        self.assertEqual(self.avaliar(municipio='Olinda'), 'DIVERGENCIA_PREFIXO')

    def test_troca_principal(self):
        self.ctx.definir(1, [V(id_prefixo=1, principal=True), V(id_prefixo=2)])
        self.ctx.definir(1, [V(id_prefixo=1), V(id_prefixo=2, principal=True)])
        links = list(self.s.scalars(select(models.UsuarioPrefixo).where(models.UsuarioPrefixo.principal.is_(True))))
        self.assertEqual([l.id_prefixo for l in links], [2])
        self.assertEqual(self.s.get(models.Usuario, 1).id_prefixo, 2)

    def test_multiplos_principais(self):
        with self.assertRaises(ContextoOperacionalError):
            self.ctx.definir(1, [V(id_prefixo=1, principal=True), V(id_prefixo=2, principal=True)])

    def test_constraint_principal(self):
        self.s.add(models.UsuarioPrefixo(id_usuario=1,id_prefixo=2,ativo=True,principal=True))
        with self.assertRaises(IntegrityError):
            self.s.flush()
        self.s.rollback()

    def test_constraint_vinculo_duplicado(self):
        self.s.add(models.UsuarioPrefixo(id_usuario=1,id_prefixo=1,ativo=True,principal=False))
        with self.assertRaises(IntegrityError):
            self.s.flush()
        self.s.rollback()

    def corrigir(self, campo, original, validado):
        extraction = self.registrar(**{campo: original})
        field = next(f for f in extraction.dados_extraidos if f.campo_identificado == campo)
        old_history = len(extraction.historico_validacao_documental)
        DadoExtraidoService(self.s).validar(field.id_dado_extraido, DadoExtraidoValidacao(valor_validado=validado))
        self.assertEqual(field.valor_extraido, original)
        self.assertEqual(field.valor_validado, validado)
        self.assertEqual(extraction.resultado_validacao_documental, 'VALIDO')
        self.assertEqual(len(extraction.historico_validacao_documental), old_history+1)
        self.assertEqual(extraction.evidencias_validacao_documental['dados_identificados'][campo], validado)

    def test_correcao_uf(self):
        self.corrigir('uf', 'BA', 'PE')

    def test_correcao_municipio(self):
        self.corrigir('municipio', 'Olinda', 'Recife')

    def test_correcao_unidade(self):
        self.corrigir('unidade_consumidora', '002', '001')

    def test_correcao_tipo(self):
        self.corrigir('tipo_documento', 'BOLETO', 'ENERGIA')

    def test_correcao_concessionaria(self):
        self.corrigir('concessionaria', 'Desconhecida', 'Empresa 1')

    def test_contrato_normaliza_consumo(self):
        extraction = self.registrar(consumo_kwh='125.5', valor_total='100', tusd='20')
        fields = {f.campo_identificado:f.valor_extraido for f in extraction.dados_extraidos}
        self.assertEqual(fields['consumo'],'125.5')
        self.assertEqual(fields['unidade_consumo'],'kWh')
        self.assertEqual(fields['valor_original'],'100')
        self.assertNotIn('consumo_kwh', fields)
        self.assertEqual(extraction.itens_extraidos[0].tipo_normalizado,'TUSD')
        self.assertEqual(extraction.itens_extraidos[0].valor, Decimal('20'))

    def test_contrato_agua(self):
        self.assertEqual(LeituraDocumental(consumo_m3='10').dados_canonicos(),dict(consumo=Decimal('10'),unidade_consumo='m3'))

    def test_contrato_conflitante(self):
        for data in (dict(consumo=1,consumo_kwh=2),dict(consumo_m3=1,consumo_kwh=1),dict(consumo_kwh=1,unidade_consumo='m3')):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                LeituraDocumental(**data)

    def test_patch_nao_altera_original(self):
        for field in ('valor_extraido','campo_identificado','id_extracao','valor_validado'):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                DadoExtraidoPatch(**{field:'x'})

    def test_regiao_configuravel(self):
        with patch.object(settings,'uf_mvp','BA'):
            self.assertEqual(self.avaliar(), 'REGIAO_NAO_SUPORTADA')

    def test_sem_contexto_nao_valida(self):
        self.assertEqual(ValidacaoDocumentalService(self.s).avaliar(self.dados)[0], 'EVIDENCIA_INSUFICIENTE')

    def test_historico_preserva_evidencias(self):
        extraction=self.registrar(uf='BA')
        field=next(f for f in extraction.dados_extraidos if f.campo_identificado=='uf')
        DadoExtraidoService(self.s).validar(field.id_dado_extraido,DadoExtraidoValidacao(valor_validado='PE'))
        self.assertEqual(extraction.historico_validacao_documental[0]['evidencias']['dados_identificados']['uf'],'BA')
        self.assertEqual(extraction.historico_validacao_documental[-1]['resultado'],'VALIDO')

    def test_revogacao_revalida(self):
        extraction=self.registrar()
        self.ctx.definir(1,[V(id_prefixo=1,ativo=False),V(id_prefixo=2,principal=True)])
        self.assertEqual(extraction.resultado_validacao_documental,'EVIDENCIA_INSUFICIENTE')

    def test_identificador_preserva_zeros(self):
        self.assertEqual(self.avaliar(unidade_consumidora='1'),'VALIDO')

    def test_endereco_sozinho_nao_comprova(self):
        self.assertEqual(self.avaliar(unidade_consumidora=None,endereco_unidade='Mesmo endereço'),'EVIDENCIA_INSUFICIENTE')

    def test_revalidacao_prefixo_conta_alterado(self):
        extraction=self.registrar()
        from app.services.conta_consumo import ContaConsumoService
        from app.schemas.conta_consumo import ContaConsumoUpdate
        ContaConsumoService(self.s).update(1,ContaConsumoUpdate(id_prefixo=2))
        self.assertEqual(extraction.resultado_validacao_documental,'DIVERGENCIA_PREFIXO')

    def test_desativacao_ultimo_prefixo_rejeitada(self):
        from app.services.prefixo import PrefixoService
        from app.schemas.prefixo import PrefixoUpdate
        with self.assertRaises(ContextoOperacionalError):
            PrefixoService(self.s).update(1,PrefixoUpdate(situacao='inativo'))
        self.assertEqual(self.ctx.resolver(1).id_prefixo,1)

    def test_desativacao_prefixo_com_alternativa(self):
        from app.services.prefixo import PrefixoService
        from app.schemas.prefixo import PrefixoUpdate
        self.ctx.definir(1,[V(id_prefixo=1),V(id_prefixo=2)])
        extraction=self.registrar()
        PrefixoService(self.s).update(1,PrefixoUpdate(situacao='inativo'))
        self.assertEqual(self.ctx.resolver(1).id_prefixo,2)
        self.assertEqual(extraction.resultado_validacao_documental,'EVIDENCIA_INSUFICIENTE')

    def test_desativacao_unidade_revalida(self):
        from app.schemas.vinculos import UnidadeConsumidoraUpdate
        extraction=self.registrar()
        unit=self.s.scalar(select(models.UnidadeConsumidora).where(
            models.UnidadeConsumidora.id_concessionaria==1,models.UnidadeConsumidora.unidade_consumidora=='001'))
        self.ctx.atualizar_unidade(unit.id_unidade_consumidora,UnidadeConsumidoraUpdate(ativo=False))
        self.assertEqual(extraction.resultado_validacao_documental,'VALIDO')
        self.assertEqual(extraction.evidencias_validacao_documental['pendencias'][0]['tipo'], 'VINCULO_UNIDADE')

    def test_uf_inexistente_nao_prova_outra_regiao(self):
        self.assertEqual(self.avaliar(uf='ZZ'),'EVIDENCIA_INSUFICIENTE')

    def test_original_revisado_protegido_no_service(self):
        extraction=self.registrar()
        field=next(f for f in extraction.dados_extraidos if f.campo_identificado=='uf')
        service=DadoExtraidoService(self.s)
        service.validar(field.id_dado_extraido,DadoExtraidoValidacao(valor_validado='PE'))
        from app.schemas.dado_extraido import DadoExtraidoUpdate
        with self.assertRaises(ContextoOperacionalError):
            service.update(field.id_dado_extraido,DadoExtraidoUpdate(valor_extraido='BA'))
        self.assertEqual(field.valor_extraido,'PE')

    def test_itens_originais_preservados_na_correcao(self):
        extraction=self.registrar(tusd='10')
        from app.services.item_extraido import ItemExtraidoService
        from app.schemas.item_extraido import ItemExtraidoValidacao
        item=extraction.itens_extraidos[0]
        ItemExtraidoService(self.s).validar(item.id_item_extraido,ItemExtraidoValidacao(valor_validado='12'))
        self.assertEqual(item.valor,Decimal('10'))
        self.assertEqual(item.valor_validado,Decimal('12'))

    def test_contrato_evitar_perda_de_precisao_monetaria(self):
        with self.assertRaises(ValidationError):
            LeituraDocumental(tusd='10.123')

    def test_navegacao_dos_vinculos_normalizados(self):
        user=self.s.get(models.Usuario,1)
        self.assertEqual(user.vinculos_prefixos[0].prefixo.localidade.municipio,'Recife')
        self.assertIs(user.vinculos_prefixos[0].usuario,user)
        unit=self.s.scalar(select(models.UnidadeConsumidora).where(
            models.UnidadeConsumidora.id_concessionaria==1,models.UnidadeConsumidora.unidade_consumidora=='001'))
        self.assertEqual(unit.prefixo.id_prefixo,1)
        self.assertEqual(unit.concessionaria.razao_social,'Empresa 1')
