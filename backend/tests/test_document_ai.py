"""Provider oficial mockado; nenhuma chamada de rede ou chave de API."""
from copy import deepcopy
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace as Obj
from typing import get_args
from unittest.mock import Mock, patch
import unittest
import httpx
import openai
from pydantic import ValidationError
from PIL import Image
from sqlalchemy import select
from tests import test_validacao_documental as foundation
from tests.test_processamento_documento import pdf, TEXT
from app.core.config import settings
from app.models import ExtracaoInteligente, DadoExtraido, Documento
from app.schemas.leitura_documental import LeituraDocumental, ContextoDocumental
from app.schemas.dado_extraido import DadoExtraidoValidacao
from app.document_ai.base import DocumentAIError, InterpretacaoAI
from app.document_ai.normalizacao import normalizar_leitura
from app.document_ai.openai_provider import OpenAIDocumentAIProvider, schema_leitura
from app.services.leitura_inteligente import LeituraInteligenteService
from app.services.dado_extraido import DadoExtraidoService
from app.processing.arquivo_documental import validar_arquivo, mime_arquivo
from app.services.exceptions import ContextoOperacionalError, UnsupportedDocumentFormatError, DocumentTooLargeError, InvalidPdfError


def raw(**fields):
    data={name:None for name in LeituraDocumental.model_fields}
    data.update(tipo_documento='CONTA_ENERGIA',concessionaria='Empresa 1',uf='PE',municipio='Recife',unidade_consumidora='001')
    data.update(fields)
    return data


def image_bytes(kind='PNG'):
    stream=BytesIO()
    Image.new('RGB',(10,10),'white').save(stream,format=kind)
    return stream.getvalue()


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self):
        self.client=Mock()
        self.response=Obj(model='modelo-resolvido',id='resp_teste',status='completed',
            usage=Obj(input_tokens=120,output_tokens=40),output=[],output_text=__import__('json').dumps(raw()))
        self.client.responses.create.return_value=self.response
        self.provider=OpenAIDocumentAIProvider(client=self.client,modelo='modelo-configuravel')

    def call(self,**fields):
        self.response.output_text=__import__('json').dumps(raw(**fields))
        return self.provider.interpretar_documento(pdf(TEXT),'application/pdf')

    def test_responses_json_schema_estrito(self):
        result=self.call()
        args=self.client.responses.create.call_args.kwargs
        self.assertEqual(args['model'],'modelo-configuravel')
        self.assertFalse(args['store'])
        schema=args['text']['format']['schema']
        self.assertTrue(args['text']['format']['strict'])
        self.assertEqual(set(schema['required']),set(LeituraDocumental.model_fields))
        self.assertFalse(schema['additionalProperties'])
        self.assertNotIn('default',str(schema))
        self.assertEqual(result.leitura.tipo_documento,'CONTA_ENERGIA')

    def test_pdf_base64_direto_sem_cadastro(self):
        self.call()
        args=self.client.responses.create.call_args.kwargs
        content=args['input'][0]['content'][0]
        self.assertEqual(content['type'],'input_file')
        self.assertTrue(content['file_data'].startswith('data:application/pdf;base64,'))
        self.assertNotIn('Recife',str(args))
        self.assertNotIn('Empresa 1',str(args))

    def test_schema_completo_sem_lookaround(self):
        patterns = {}

        def revisar(node, path='$'):
            if isinstance(node, dict):
                if 'pattern' in node:
                    patterns[path] = node['pattern']
                    for construct in ('(?=', '(?!', '(?<=', '(?<!'):
                        self.assertNotIn(construct, node['pattern'], path)
                for key, value in node.items():
                    revisar(value, f'{path}.{key}')
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    revisar(value, f'{path}[{index}]')

        revisar(schema_leitura())
        self.assertEqual(set(patterns), {
            '$.properties.competencia.anyOf[0]', '$.properties.uf.anyOf[0]'})

    def test_todos_decimais_no_contrato_sao_numeros_nullable(self):
        schema = schema_leitura()
        for name, field in LeituraDocumental.model_fields.items():
            if Decimal in get_args(field.annotation):
                with self.subTest(campo=name):
                    branches = schema['properties'][name]['anyOf']
                    self.assertEqual([branch['type'] for branch in branches], ['number', 'null'])
                    self.assertEqual(branches[0]['minimum'], 0)
        self.assertEqual(schema['properties']['percentual_esgoto']['anyOf'][0]['maximum'], 100)

    def test_validacao_monetaria_preservada_apos_schema(self):
        schema_leitura()
        for name, field in LeituraDocumental.model_fields.items():
            if any(getattr(rule, 'decimal_places', None) == 2 for rule in field.metadata):
                for value in ('-0.01', '0.001', '1000000000000.00'):
                    with self.subTest(campo=name, valor=value), self.assertRaises(ValidationError):
                        LeituraDocumental.model_validate({name: value})
                self.assertEqual(getattr(LeituraDocumental.model_validate({name: '123.45'}), name), Decimal('123.45'))

    def test_png_multimodal(self):
        self.provider.interpretar_documento(image_bytes(),'image/png')
        content=self.client.responses.create.call_args.kwargs['input'][0]['content'][0]
        self.assertEqual(content['type'],'input_image')
        self.assertTrue(content['image_url'].startswith('data:image/png;base64,'))

    def test_jpeg_multimodal(self):
        self.provider.interpretar_documento(image_bytes('JPEG'),'image/jpeg')
        self.assertEqual(self.client.responses.create.call_args.kwargs['input'][0]['content'][0]['type'],'input_image')

    def test_usage_real_sem_confianca_inventada(self):
        result=self.call()
        self.assertEqual(result.metadados['tokens_entrada'],120)
        self.assertEqual(result.metadados['tokens_saida'],40)
        self.assertEqual(result.metadados['modelo'],'modelo-resolvido')
        self.assertNotIn('confianca',result.metadados)

    def test_usage_ausente_nao_estimado(self):
        self.response.usage=None
        result=self.call()
        self.assertIsNone(result.metadados['tokens_entrada'])

    def test_tipo_fora_do_mvp(self):
        with self.assertRaises(DocumentAIError):
            self.call(tipo_documento='ENERGIA')

    def test_tipo_ambiguo_nullable(self):
        self.assertIsNone(self.call(tipo_documento=None).leitura.tipo_documento)

    def test_json_invalido(self):
        self.response.output_text='texto livre'
        with self.assertRaises(DocumentAIError) as error:
            self.provider.interpretar_documento(pdf(TEXT),'application/pdf')
        self.assertEqual(error.exception.codigo,'resposta_invalida')
        self.assertEqual(error.exception.metadados['tokens_entrada'],120)

    def test_campos_inesperados(self):
        with self.assertRaises(DocumentAIError):
            self.call(resultado_validacao_documental='VALIDO')

    def test_resposta_incompleta(self):
        self.response.status='incomplete'
        with self.assertRaises(DocumentAIError) as error:
            self.call()
        self.assertEqual(error.exception.codigo,'resposta_incompleta')

    def test_resposta_vazia(self):
        self.response.output_text=''
        with self.assertRaises(DocumentAIError) as error:
            self.provider.interpretar_documento(pdf(TEXT),'application/pdf')
        self.assertEqual(error.exception.codigo,'resposta_vazia')

    def test_recusa(self):
        self.response.output=[Obj(content=[Obj(type='refusal')])]
        with self.assertRaises(DocumentAIError) as error:
            self.call()
        self.assertEqual(error.exception.codigo,'recusa_modelo')

    def test_todos_campos_nulos_sem_conteudo_utilizavel(self):
        self.response.output_text=__import__('json').dumps({name:None for name in LeituraDocumental.model_fields})
        with self.assertRaises(DocumentAIError) as error:
            self.provider.interpretar_documento(pdf(TEXT),'application/pdf')
        self.assertEqual(error.exception.codigo,'resposta_vazia')

    def test_pydantic_rejeita_valor_invalido(self):
        for fields in (dict(valor_total='valor desconhecido'),dict(uf=123),dict(unidade_consumo=[])):
            with self.subTest(fields=fields),self.assertRaises(DocumentAIError):
                self.call(**fields)

    def test_timeout(self):
        self.client.responses.create.side_effect=openai.APITimeoutError(request=httpx.Request('POST','https://example.test'))
        with self.assertRaises(DocumentAIError) as error:
            self.call()
        self.assertEqual(error.exception.codigo,'timeout')
        self.assertEqual(error.exception.http_status,504)

    def erro_sdk(self,klass,status,expected):
        response=httpx.Response(status,request=httpx.Request('POST','https://example.test'))
        self.client.responses.create.side_effect=klass('conteudo-nao-logar',response=response,body={'detail':'nao-expor'})
        with self.assertRaises(DocumentAIError) as error:
            self.call()
        self.assertEqual(error.exception.codigo,expected)
        self.assertNotIn('conteudo',str(error.exception))
        self.assertNotIn('nao-expor',str(error.exception.metadados))

    def test_rate_limit(self):
        self.erro_sdk(openai.RateLimitError,429,'rate_limit')

    def test_autenticacao(self):
        self.erro_sdk(openai.AuthenticationError,401,'autenticacao_provider')

    def test_indisponibilidade(self):
        self.erro_sdk(openai.InternalServerError,503,'provider_indisponivel')

    def test_bad_request(self):
        self.erro_sdk(openai.BadRequestError,400,'requisicao_provider_invalida')

    def test_modelo_nao_configurado(self):
        provider=OpenAIDocumentAIProvider(client=self.client,modelo='')
        with self.assertRaises(DocumentAIError) as error:
            provider.interpretar_documento(pdf(TEXT),'application/pdf')
        self.assertEqual(error.exception.codigo,'configuracao_ausente')
        self.client.responses.create.assert_not_called()

    def test_chave_ausente(self):
        with patch.object(settings,'openai_api_key',''):
            with self.assertRaises(DocumentAIError):
                OpenAIDocumentAIProvider(modelo='modelo-teste').interpretar_documento(pdf(TEXT),'application/pdf')

    def test_pdf_invalido_nao_envia(self):
        with self.assertRaises(InvalidPdfError):
            self.provider.interpretar_documento(b'%PDF-quebrado','application/pdf')
        self.client.responses.create.assert_not_called()


class AIFlowTests(unittest.TestCase):
    def setUp(self):
        foundation.ValidacaoDocumentalTests.setUp(self)
        self.provider=Mock(provider='openai',modelo='modelo-teste')
        self.storage=Mock()
        self.storage.read.return_value=pdf(TEXT)
        self.service=LeituraInteligenteService(self.s,self.storage,self.provider)
        self.context=ContextoDocumental(id_usuario=1)

    def executar(self,**fields):
        original=raw(**fields)
        result=InterpretacaoAI(normalizar_leitura(original),original,dict(provider='openai',modelo='modelo-teste',
            status='concluida',tokens_entrada=120,tokens_saida=40,latencia_ms=15))
        self.provider.interpretar_documento.return_value=result
        return self.service.processar(1,self.context)

    def test_energia_pe(self):
        self.assertEqual(self.executar().extracao.resultado_validacao_documental,'VALIDO')

    def test_agua_pe(self):
        result=self.executar(tipo_documento='CONTA_AGUA',concessionaria='Empresa 2',consumo_m3='15',tarifa_agua='50',tarifa_esgoto='40')
        self.assertEqual(result.extracao.resultado_validacao_documental,'VALIDO')
        self.assertEqual({i.tipo_normalizado for i in result.itens_encontrados},{'TARIFA_AGUA','TARIFA_ESGOTO'})

    def test_boleto_generico(self):
        self.assertEqual(self.executar(tipo_documento='OUTRO').extracao.resultado_validacao_documental,'DOCUMENTO_NAO_SUPORTADO')

    def test_ambiguo(self):
        self.assertEqual(self.executar(tipo_documento=None).extracao.resultado_validacao_documental,'EVIDENCIA_INSUFICIENTE')

    def test_energia_ba(self):
        self.assertEqual(self.executar(uf='BA').extracao.resultado_validacao_documental,'REGIAO_NAO_SUPORTADA')

    def test_agua_al(self):
        self.assertEqual(self.executar(tipo_documento='CONTA_AGUA',uf='AL').extracao.resultado_validacao_documental,'REGIAO_NAO_SUPORTADA')

    def test_sem_uf(self):
        self.assertEqual(self.executar(uf=None).extracao.resultado_validacao_documental,'EVIDENCIA_INSUFICIENTE')

    def test_sem_unidade(self):
        self.assertEqual(self.executar(unidade_consumidora=None).extracao.resultado_validacao_documental,'EVIDENCIA_INSUFICIENTE')

    def test_componentes_e_consumo(self):
        result=self.executar(valor_total='200.15',consumo_kwh='123.45',tusd='50',te='40',icms='20',pis='1',cofins='2',descontos='3',multas='4',juros='5')
        fields={f.campo_identificado:f.valor_extraido for f in result.campos_encontrados}
        self.assertEqual(fields['valor_original'],'200.15')
        self.assertEqual(fields['consumo'],'123.45')
        self.assertEqual(fields['unidade_consumo'],'kWh')
        self.assertNotIn('consumo_kwh',fields)
        self.assertEqual({i.tipo_normalizado for i in result.itens_encontrados},{'TUSD','TE','ICMS','PIS','COFINS','DESCONTO','MULTA','JUROS'})
        self.assertIsNone(result.confianca_geral)
        self.assertTrue(all(i.nivel_confianca is None for i in result.itens_encontrados))

    def test_preserva_original_e_normalizado(self):
        result=self.executar(uf=' pe ',valor_total='R$ 1.234,56')
        extraction=self.s.get(ExtracaoInteligente,result.extracao.id_extracao)
        uf=next(f for f in extraction.dados_extraidos if f.campo_identificado=='uf')
        self.assertEqual(uf.valor_extraido,' pe ')
        self.assertEqual(uf.valor_normalizado,'PE')
        self.assertEqual(extraction.resposta_original_ia['uf'],' pe ')
        self.assertEqual(extraction.resultado_validacao_documental,'VALIDO')
        value=next(f for f in extraction.dados_extraidos if f.campo_identificado=='valor_original')
        DadoExtraidoService(self.s).validar(value.id_dado_extraido,DadoExtraidoValidacao())
        self.assertEqual(value.valor_extraido,'R$ 1.234,56')
        self.assertEqual(value.valor_validado,'1234.56')

    def test_idempotencia(self):
        first=self.executar()
        second=self.service.processar(1,self.context)
        self.assertEqual(first.model_dump(),second.model_dump())
        self.provider.interpretar_documento.assert_called_once()
        self.assertEqual(len(self.s.get(Documento,1).historico_leitura_ia),1)

    def test_correcao_humana_preservada(self):
        first=self.executar(uf='BA')
        uf=next(f for f in first.campos_encontrados if f.campo_identificado=='uf')
        DadoExtraidoService(self.s).validar(uf.id_dado_extraido,DadoExtraidoValidacao(valor_validado='PE'))
        second=self.service.processar(1,self.context)
        corrected=next(f for f in second.campos_encontrados if f.campo_identificado=='uf')
        self.assertEqual(corrected.valor_extraido,'BA')
        self.assertEqual(corrected.valor_validado,'PE')
        self.assertEqual(second.extracao.resultado_validacao_documental,'VALIDO')
        self.provider.interpretar_documento.assert_called_once()

    def test_reprocessamento_explicito_preserva_anterior(self):
        first=self.executar(uf='BA')
        uf=next(f for f in first.campos_encontrados if f.campo_identificado=='uf')
        DadoExtraidoService(self.s).validar(uf.id_dado_extraido,DadoExtraidoValidacao(valor_validado='PE'))
        second=self.service.processar(1,self.context,reprocessar=True)
        self.assertNotEqual(first.extracao.id_extracao,second.extracao.id_extracao)
        self.assertEqual(self.s.get(DadoExtraido,uf.id_dado_extraido).valor_validado,'PE')

    def test_metadados_persistidos(self):
        result=self.executar()
        extraction=self.s.get(ExtracaoInteligente,result.extracao.id_extracao)
        self.assertEqual(extraction.metadados_ia['provider'],'openai')
        self.assertEqual(extraction.metadados_ia['modelo'],'modelo-teste')
        self.assertEqual(extraction.metadados_ia['tokens_entrada'],120)
        self.assertEqual(extraction.metadados_ia['tokens_saida'],40)

    def test_erro_nao_apaga_extracao_anterior(self):
        first=self.executar()
        self.provider.interpretar_documento.side_effect=DocumentAIError('timeout',504)
        with self.assertRaises(DocumentAIError):
            self.service.processar(1,self.context,reprocessar=True)
        self.assertEqual(len(list(self.s.scalars(select(ExtracaoInteligente)))),1)
        self.assertEqual(self.s.get(ExtracaoInteligente,first.extracao.id_extracao).resultado_validacao_documental,'VALIDO')
        self.assertEqual(self.s.get(Documento,1).historico_leitura_ia[-1]['erro_tecnico'],'timeout')

    def test_resposta_invalida_sem_persistencia_parcial(self):
        self.provider.interpretar_documento.return_value='texto livre'
        with self.assertRaises(DocumentAIError):
            self.service.processar(1,self.context)
        self.assertEqual(list(self.s.scalars(select(ExtracaoInteligente))),[])
        self.assertEqual(list(self.s.scalars(select(DadoExtraido))),[])
        self.assertEqual(self.s.get(Documento,1).historico_leitura_ia[-1]['status'],'erro')

    def test_contexto_nao_autorizado_antes_da_api(self):
        with self.assertRaises(ContextoOperacionalError):
            self.service.processar(1,ContextoDocumental(id_usuario=1,id_prefixo=2))
        self.provider.interpretar_documento.assert_not_called()

    def test_contexto_ausente_antes_da_api(self):
        with self.assertRaises(ContextoOperacionalError):
            self.service.processar(1,None)
        self.provider.interpretar_documento.assert_not_called()

    def test_limite_tamanho_antes_da_api(self):
        with patch.object(settings,'document_max_size_bytes',1),self.assertRaises(DocumentAIError) as error:
            self.service.processar(1,self.context)
        self.assertEqual(error.exception.http_status,413)
        self.provider.interpretar_documento.assert_not_called()
        self.assertEqual(list(self.s.scalars(select(ExtracaoInteligente))),[])

    def test_logs_nao_expoem_payload(self):
        self.provider.interpretar_documento.side_effect=DocumentAIError('resposta_invalida')
        with self.assertLogs('app.services.leitura_inteligente',level='WARNING') as captured:
            with self.assertRaises(DocumentAIError):
                self.service.processar(1,self.context)
        self.assertTrue(all('Empresa' not in line and 'Recife' not in line for line in captured.output))

    def test_validador_executado_apos_interpretacao(self):
        with patch('app.services.interpretacao_documental.ValidacaoDocumentalService', wraps=__import__('app.services.validacao_documental',fromlist=['ValidacaoDocumentalService']).ValidacaoDocumentalService) as validator:
            self.executar()
            validator.assert_called_once_with(self.s)


class NormalizacaoArquivoTests(unittest.TestCase):
    def test_normalizacao_de_campos(self):
        result=normalizar_leitura(raw(uf=' pe ',concessionaria=' Empresa  1 ',data_vencimento='20/10/2026',competencia='10/2026',consumo_kwh='1.234,500',unidade_consumo='KWH'))
        self.assertEqual(result.uf,'PE')
        self.assertEqual(result.concessionaria,'Empresa 1')
        self.assertEqual(result.data_vencimento.isoformat(),'2026-10-20')
        self.assertEqual(result.competencia,'2026-10')
        self.assertEqual(result.consumo_kwh,Decimal('1234.500'))

    def test_codigo_barras_sem_reinterpretar(self):
        self.assertEqual(normalizar_leitura(raw(codigo_barras='1'*22+' '+'2'*22)).codigo_barras,'1'*22+'2'*22)
        with self.assertRaises(DocumentAIError):
            normalizar_leitura(raw(codigo_barras='123'))

    def test_formatos_fechados(self):
        for filename,mime in [('a.pdf','application/pdf'),('a.jpg','image/jpeg'),('a.jpeg','image/jpeg'),('a.PNG','image/png')]:
            self.assertEqual(mime_arquivo(filename,mime),mime)
        for filename,mime in [('a.exe','application/pdf'),('a.png','image/jpeg'),('a.svg','image/svg+xml')]:
            with self.assertRaises(UnsupportedDocumentFormatError):
                mime_arquivo(filename,mime)

    def test_imagem_falsa_rejeitada(self):
        with self.assertRaises(UnsupportedDocumentFormatError):
            validar_arquivo(b'nao-e-imagem','image/png')

    def test_tamanho_limitado(self):
        with patch.object(settings,'document_max_size_bytes',10),self.assertRaises(DocumentTooLargeError):
            validar_arquivo(b'X'*11,'application/pdf')

    def test_numero_ambiguo_nao_inferido(self):
        for value in ('1 234',True,'12,34,56'):
            with self.subTest(value=value),self.assertRaises(DocumentAIError):
                normalizar_leitura(raw(valor_total=value))
