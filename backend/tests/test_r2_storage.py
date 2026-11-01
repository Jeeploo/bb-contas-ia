"""Storage local/R2 e integração documental sem rede ou providers reais."""
import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError, EndpointConnectionError
from botocore.response import StreamingBody
from sqlalchemy.orm import Session
from app.core.config import Settings, settings
from app.models import Documento
from app.processing.storage import LocalDocumentStorage, get_document_storage
from app.processing.r2_storage import R2DocumentStorage
from app.services.exceptions import (DocumentFileNotFoundError, DocumentStorageError,
    DocumentTooLargeError, InvalidPdfError, UnsupportedDocumentFormatError)
from app.services.processamento_documento import ProcessamentoDocumentoService
from app.schemas.leitura_documental import ContextoDocumental
from app.document_ai.base import InterpretacaoAI
from app.document_ai.normalizacao import normalizar_leitura
from tests.test_api import ApiTestCase, ENTITIES
from tests.test_processamento_documento import pdf, TEXT
from tests.test_document_ai import raw

R2_CONFIG=dict(r2_endpoint='https://account-test.r2.cloudflarestorage.com',r2_bucket='contas-test',
    r2_access_key_id='access-test-only',r2_secret_access_key='secret-test-only',r2_region='auto')


def missing():
    return ClientError({'Error':{'Code':'NoSuchKey','Message':'sensitive provider details'}},'GetObject')


class StorageUnitTests(unittest.TestCase):
    def setUp(self):
        network=patch('socket.socket.connect',side_effect=AssertionError('Rede proibida'))
        network.start();self.addCleanup(network.stop)
        self.data=pdf(TEXT);self.s3=Mock()
        self.storage=R2DocumentStorage(bucket='contas-test',client=self.s3)

    def test_local_save_read_delete_and_missing(self):
        with TemporaryDirectory() as directory:
            local=LocalDocumentStorage(directory)
            key=local.save(BytesIO(self.data),'original-privado.pdf','application/pdf')
            self.assertEqual(local.provider,'local')
            self.assertNotIn('original',key)
            self.assertEqual(local.read(key),self.data)
            local.delete(key)
            with self.assertRaises(DocumentFileNotFoundError):local.read(key)

    def test_r2_save_private_key_hash_no_original_filename(self):
        key=self.storage.save(BytesIO(self.data),'unidade-privada.pdf','application/pdf')
        digest=hashlib.sha256(self.data).hexdigest()
        self.assertRegex(key,r'^documentos/[0-9a-f]{32}/'+digest+r'\.pdf$')
        self.assertNotIn('privada',key)
        self.s3.put_object.assert_called_once_with(Bucket='contas-test',Key=key,Body=self.data,ContentType='application/pdf')
        for forbidden in ('create_bucket','put_bucket_acl','put_bucket_policy','generate_presigned_url'):
            getattr(self.s3,forbidden).assert_not_called()
        self.assertNotIn('ACL',self.s3.put_object.call_args.kwargs)

    def test_r2_read_limits_and_closes_stream(self):
        key=self.storage.save(BytesIO(self.data),'conta.pdf','application/pdf')
        stream=Mock(wraps=BytesIO(self.data))
        self.s3.get_object.return_value={'Body':stream,'ContentLength':len(self.data)}
        self.assertEqual(self.storage.read(key),self.data)
        stream.read.assert_called_once_with(self.storage.max_size+1)
        stream.close.assert_called_once()
        self.s3.get_object.assert_called_once_with(Bucket='contas-test',Key=key)

    def test_r2_missing_and_provider_error_sanitized(self):
        key=self.storage.save(BytesIO(self.data),'conta.pdf','application/pdf')
        self.s3.get_object.side_effect=missing()
        with self.assertRaises(DocumentFileNotFoundError) as error:self.storage.read(key)
        self.assertNotIn('sensitive',str(error.exception))
        self.s3.get_object.side_effect=EndpointConnectionError(endpoint_url='https://secret.invalid')
        with self.assertRaises(DocumentStorageError) as error:self.storage.read(key)
        self.assertNotIn('secret',str(error.exception))
        self.assertTrue(error.exception.__suppress_context__)

    def test_r2_rejects_invalid_upload_before_sdk(self):
        for data,name,mime,error in [(b'invalid','conta.pdf','application/pdf',InvalidPdfError),
            (self.data,'file.txt','text/plain',UnsupportedDocumentFormatError)]:
            with self.assertRaises(error):self.storage.save(BytesIO(data),name,mime)
        self.s3.put_object.assert_not_called()
        with self.assertRaises(DocumentTooLargeError):
            R2DocumentStorage(bucket='test',client=self.s3,max_size=4).save(BytesIO(self.data),'c.pdf','application/pdf')
        self.s3.put_object.assert_not_called()

    def test_r2_read_oversize_by_header_or_bytes_closes_stream(self):
        key=self.storage.save(BytesIO(self.data),'conta.pdf','application/pdf')
        small=R2DocumentStorage(bucket='test',client=self.s3,max_size=4)
        for length in (999,0):
            stream=Mock(wraps=BytesIO(self.data))
            self.s3.get_object.return_value={'Body':stream,'ContentLength':length}
            with self.assertRaises(DocumentTooLargeError):small.read(key)
            stream.close.assert_called_once()

    def test_r2_delete_and_invalid_key(self):
        key=self.storage.save(BytesIO(self.data),'conta.pdf','application/pdf')
        self.storage.delete(key)
        self.s3.delete_object.assert_called_once_with(Bucket='contas-test',Key=key)
        with self.assertRaises(UnsupportedDocumentFormatError):self.storage.read('../../arquivo.pdf')
        self.s3.get_object.assert_not_called()
        self.s3.delete_object.side_effect=missing()
        with self.assertRaises(DocumentStorageError):self.storage.delete(key)

    def test_r2_factory_explicit_credentials_and_no_network_on_init(self):
        with patch.multiple(settings,document_storage_provider='r2',**R2_CONFIG),patch('app.processing.r2_storage.boto3.client',return_value=self.s3) as client:
            storage=get_document_storage()
            client.assert_not_called()
            storage.save(BytesIO(self.data),'conta.pdf','application/pdf')
            args=client.call_args.kwargs
            self.assertEqual(args['endpoint_url'],R2_CONFIG['r2_endpoint'])
            self.assertEqual(args['aws_access_key_id'],R2_CONFIG['r2_access_key_id'])
            self.assertEqual(args['aws_secret_access_key'],R2_CONFIG['r2_secret_access_key'])
            self.assertEqual(args['region_name'],'auto')
            self.assertEqual(args['config'].retries['total_max_attempts'],1)
        with patch('app.processing.r2_storage.boto3.client') as client:
            with self.assertRaises(DocumentStorageError):R2DocumentStorage(bucket='test').read('documentos/'+'0'*32+'/'+'0'*64+'.pdf')
            client.assert_not_called()

    def test_config_r2_permite_host_efemero_e_local_default(self):
        self.assertEqual(Settings({}).document_storage_provider,'local')
        values=dict(APP_ENV='homologation',FRONTEND_ORIGIN='https://app.exemplo.com',
            DATABASE_URL='postgresql://u:p@db.exemplo.com/demo',DOCUMENT_STORAGE_PROVIDER='r2',
            R2_ENDPOINT=R2_CONFIG['r2_endpoint'],R2_BUCKET='test',R2_ACCESS_KEY_ID='test',R2_SECRET_ACCESS_KEY='test')
        config=Settings(values)
        self.assertFalse(config.document_storage_persistent)
        self.assertEqual(config.document_storage_path,'./storage/documentos')
        for field in ('R2_ENDPOINT','R2_BUCKET','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY'):
            invalid={**values,field:''}
            with self.subTest(field=field),self.assertRaises(ValueError):Settings(invalid)
        with self.assertRaises(ValueError):Settings({**values,'R2_ENDPOINT':'http://insecure.example'})
        with self.assertRaises(ValueError):Settings({'DOCUMENT_STORAGE_PROVIDER':'unknown'})


class R2DocumentFlowTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        for resource,_,payload,_ in ENTITIES[:4]:self.client.post('/api/v1/'+resource,json=payload)
        self.client.post('/api/v1/usuarios',json=dict(matricula='TEST',nome='Operador',funcao='operador',situacao='ativo',id_prefixo=1))
        self.client.post('/api/v1/unidades_consumidoras',json=dict(id_prefixo=1,id_concessionaria=1,unidade_consumidora='001'))
        directory=TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.local_path=Path(directory.name)/'documents'
        config=patch.multiple(settings,document_storage_provider='r2',document_storage_path=str(self.local_path),**R2_CONFIG)
        config.start();self.addCleanup(config.stop)
        self.objects={};self.s3=Mock()
        self.s3.put_object.side_effect=lambda **kw:self.objects.update({kw['Key']:kw['Body']})
        def read(**kw):
            if kw['Key'] not in self.objects:raise missing()
            data=self.objects[kw['Key']]
            return {'Body':StreamingBody(BytesIO(data),len(data)),'ContentLength':len(data)}
        self.s3.get_object.side_effect=read
        self.s3.delete_object.side_effect=lambda **kw:self.objects.pop(kw['Key'],None)
        adapter=patch('app.processing.r2_storage.boto3.client',return_value=self.s3)
        self.factory=adapter.start();self.addCleanup(adapter.stop)
        self.provider=Mock(provider='gemini',modelo='simulado')
        original=raw(concessionaria='Teste',competencia='09/2026',valor_total='736,53',data_vencimento='20/10/2026',consumo_kwh='523')
        self.provider.interpretar_documento.return_value=InterpretacaoAI(normalizar_leitura(original),original,dict(status='concluida'))
        provider=patch('app.services.leitura_inteligente.get_document_ai_provider',return_value=self.provider)
        provider.start();self.addCleanup(provider.stop)
        self.data=pdf(TEXT)
        network=patch('socket.socket.connect',side_effect=AssertionError('Rede proibida'))
        network.start();self.addCleanup(network.stop)

    def upload(self,legacy=False):
        path='/api/v1/contas_consumo/1/documentos/upload' if legacy else '/api/v1/documentos/upload'
        return self.client.post(path,params=dict(id_usuario=1),files={'file':('conta-privada.pdf',self.data,'application/pdf')})

    def process(self,id,**params):
        return self.client.post(f'/api/v1/documentos/{id}/processar-inteligente',params=dict(id_usuario=1,**params))

    def test_upload_referencia_persistida_sem_disco_e_ia_recebe_bytes(self):
        for provider in ('gemini','openai'):
            self.provider.provider=provider
            response=self.upload();self.assertEqual(response.status_code,201,response.text)
            doc=response.json();self.assertIn('documentos/',doc['caminho_arquivo'])
            with Session(self.engine) as session:
                saved=session.get(Documento,doc['id_documento'])
                self.assertEqual(saved.storage_provider,'r2')
                self.assertEqual(saved.storage_key,doc['caminho_arquivo'])
            result=self.process(doc['id_documento']);self.assertEqual(result.status_code,200,result.text)
            self.provider.interpretar_documento.assert_called_with(self.data,'application/pdf')
            self.assertEqual(result.json()['metadados_ia']['sha256_documento'],hashlib.sha256(self.data).hexdigest())
        self.assertFalse(self.local_path.exists())

    def test_idempotencia_reprocessamento_e_conta_nao_duplica(self):
        id=self.upload().json()['id_documento']
        first=self.process(id);second=self.process(id)
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json(),second.json())
        self.provider.interpretar_documento.assert_called_once()
        count=len(self.client.get('/api/v1/contas_consumo').json())
        result=self.process(id,reprocessar=True);self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.provider.interpretar_documento.call_count,2)
        self.assertEqual(len(self.client.get('/api/v1/contas_consumo').json()),count)
        self.assertEqual(len(self.objects),1)

    def test_arquivo_local_antigo_continua_local_com_default_r2(self):
        with patch.object(settings,'document_storage_provider','local'):
            id=self.upload().json()['id_documento']
        with Session(self.engine) as session:
            document=session.get(Documento,id);document.storage_key=None;session.commit()
        result=self.process(id)
        self.assertEqual(result.status_code,200,result.text)
        self.provider.interpretar_documento.assert_called_once_with(self.data,'application/pdf')
        self.factory.assert_not_called()
        self.assertTrue(self.local_path.exists())

    def test_documento_r2_lido_apos_default_mudar_para_local(self):
        id=self.upload().json()['id_documento']
        with patch.object(settings,'document_storage_provider','local'):
            result=self.process(id)
        self.assertEqual(result.status_code,200,result.text)
        self.provider.interpretar_documento.assert_called_with(self.data,'application/pdf')
        self.assertFalse(self.local_path.exists())

    def test_objeto_ausente_e_falha_storage_nao_chamam_ia(self):
        id=self.upload().json()['id_documento'];self.objects.clear()
        response=self.process(id);self.assertEqual(response.status_code,404,response.text)
        self.s3.get_object.side_effect=EndpointConnectionError(endpoint_url='https://secret.invalid')
        response=self.process(id);self.assertEqual(response.status_code,503,response.text)
        self.assertEqual(response.json()['detail']['codigo'],'storage_indisponivel')
        self.assertNotIn('secret',response.text)
        self.provider.interpretar_documento.assert_not_called()

    def test_erro_upload_sem_fallback_nem_documento_parcial(self):
        self.s3.put_object.side_effect=ClientError({'Error':{'Code':'AccessDenied','Message':'secret-test-only'}},'PutObject')
        response=self.upload();self.assertEqual(response.status_code,503,response.text)
        self.assertNotIn('secret-test-only',response.text)
        self.assertEqual(self.client.get('/api/v1/documentos').json(),[])
        self.assertFalse(self.local_path.exists())

    def test_upload_legado_e_extracao_deterministica_tambem_usam_r2(self):
        response=self.upload(legacy=True);self.assertEqual(response.status_code,201,response.text)
        id=response.json()['id_documento']
        result=self.client.post(f'/api/v1/documentos/{id}/processar',params=dict(id_usuario=1))
        self.assertEqual(result.status_code,200,result.text)
        self.assertTrue(any(f['campo_identificado']=='valor_original' for f in result.json()['campos_encontrados']))
        self.assertFalse(self.local_path.exists())
        self.provider.interpretar_documento.assert_not_called()

    def test_rollback_remove_objeto_sem_mascarar_erro_original(self):
        with Session(self.engine) as session:
            service=ProcessamentoDocumentoService(session)
            with patch.object(session,'commit',side_effect=RuntimeError('transaction-failed')):
                with self.assertRaisesRegex(RuntimeError,'transaction-failed'):
                    service.upload_inicial(BytesIO(self.data),'conta.pdf','application/pdf',ContextoDocumental(id_usuario=1))
        self.assertEqual(self.objects,{})
        self.s3.delete_object.assert_called_once()
        self.assertEqual(self.client.get('/api/v1/documentos').json(),[])


class StorageMigrationTests(unittest.TestCase):
    def test_migration_preserva_referencia_e_arquivo_local_e_bloqueia_downgrade_r2(self):
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import create_engine, text
        from app.processing.storage import storage_for_document, document_storage_key
        with TemporaryDirectory() as directory:
            url='sqlite:///'+str(Path(directory)/'migration.db')
            local=LocalDocumentStorage(str(Path(directory)/'files'))
            data=pdf(TEXT);key=local.save(BytesIO(data),'antigo.pdf','application/pdf')
            with patch.object(settings,'database_url',url):
                config=Config('alembic.ini');command.upgrade(config,'d45f3a21b001')
                engine=create_engine(url);self.addCleanup(engine.dispose)
                with engine.begin() as connection:
                    connection.execute(text("INSERT INTO documentos (id_documento,tipo_documento,formato,data_recebimento,origem,caminho_arquivo) VALUES (1,'fatura','pdf',CURRENT_TIMESTAMP,'upload',:key)"),{'key':key})
                command.upgrade(config,'head')
                with Session(engine) as session,patch.object(settings,'document_storage_path',str(local.directory)),patch.object(settings,'document_storage_provider','r2'):
                    document=session.get(Documento,1)
                    self.assertEqual(document.storage_provider,'local')
                    self.assertEqual(document.storage_key,key)
                    self.assertEqual(document.caminho_arquivo,key)
                    self.assertEqual(storage_for_document(document).read(document_storage_key(document)),data)
                self.assertEqual(local.read(key),data)
                with engine.begin() as connection:
                    connection.execute(text("UPDATE documentos SET storage_provider='r2' WHERE id_documento=1"))
                with self.assertRaisesRegex(RuntimeError,'Downgrade bloqueado'):
                    command.downgrade(config,'d45f3a21b001')
                self.assertEqual(local.read(key),data)
