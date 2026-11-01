from sqlalchemy.orm import Session
from tests.test_api import ApiTestCase, ENTITIES
from tests.test_processamento_documento import pdf, TEXT
from unittest.mock import patch
from tempfile import TemporaryDirectory
from app.core.config import settings
from app.models import Usuario, UsuarioPrefixo


class ContextoDocumentalApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        for resource, _, payload, _ in ENTITIES[:5]:
            response=self.client.post('/api/v1/'+resource,json=payload)
            self.assertEqual(response.status_code,201,response.text)
        response=self.client.post('/api/v1/usuarios',json=dict(matricula='U',nome='Operador',funcao='operador',situacao='ativo',id_prefixo=1))
        self.assertEqual(response.status_code,201,response.text)
        self.leitura=dict(tipo_documento='ENERGIA',uf='PE',municipio='Recife',concessionaria='Teste',unidade_consumidora='001')
        response=self.client.post('/api/v1/unidades_consumidoras',json=dict(id_prefixo=1,id_concessionaria=1,unidade_consumidora='001'))
        self.assertEqual(response.status_code,201,response.text)

    def registrar(self,**changes):
        return self.client.post('/api/v1/documentos/1/interpretacao',json=dict(
            leitura={**self.leitura,**changes},contexto=dict(id_usuario=1)))

    def test_entrada_tipado_e_revalidacao(self):
        response=self.registrar()
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(response.json()['resultado_validacao_documental'],'VALIDO')
        id_extracao=response.json()['id_extracao']
        repeated=self.client.post(f'/api/v1/extracoes_inteligentes/{id_extracao}/revalidar',json=dict(id_usuario=1))
        self.assertEqual(repeated.status_code,200,repeated.text)
        self.assertEqual(len(repeated.json()['historico_validacao_documental']),2)

    def test_patch_original_bloqueado(self):
        self.assertEqual(self.registrar().status_code,201)
        field=self.client.get('/api/v1/dados_extraidos').json()[0]
        for changes in (dict(valor_extraido='X'),dict(campo_identificado='X'),dict(id_extracao=999),dict(valor_validado='X')):
            with self.subTest(changes=changes):
                response=self.client.patch(f"/api/v1/dados_extraidos/{field['id_dado_extraido']}",json=changes)
                self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(self.client.get(f"/api/v1/dados_extraidos/{field['id_dado_extraido']}").json(),field)

    def test_correcao_humana_revalida(self):
        extraction=self.registrar(uf='BA').json()
        fields=self.client.get('/api/v1/dados_extraidos').json()
        uf=next(f for f in fields if f['campo_identificado']=='uf')
        response=self.client.patch(f"/api/v1/dados_extraidos/{uf['id_dado_extraido']}/validacao",json=dict(valor_validado='PE'))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['valor_extraido'],'BA')
        extraction=self.client.get(f"/api/v1/extracoes_inteligentes/{extraction['id_extracao']}").json()
        self.assertEqual(extraction['resultado_validacao_documental'],'VALIDO')
        self.assertEqual(len(extraction['historico_validacao_documental']),2)

    def test_usuario_operacional_sem_prefixo_rejeitado(self):
        response=self.client.post('/api/v1/usuarios',json=dict(matricula='SEM',nome='Sem',funcao='operador',situacao='ativo'))
        self.assertEqual(response.status_code,403,response.text)

    def test_vinculos_duplicados_e_multiplos_principais(self):
        for links in ([dict(id_prefixo=1),dict(id_prefixo=1)],[]):
            response=self.client.put('/api/v1/usuarios/1/prefixos',json=dict(vinculos=links))
            self.assertEqual(response.status_code,403,response.text)

    def test_contexto_nao_autorizado_impede_processar_antes_de_ler(self):
        prefix={**ENTITIES[1][2], 'codigo_prefixo':'OUTRO'}
        self.assertEqual(self.client.post('/api/v1/prefixos',json=prefix).status_code,201)
        response=self.client.post('/api/v1/documentos/1/processar',params=dict(id_usuario=1,id_prefixo=2))
        self.assertEqual(response.status_code,403,response.text)
        self.assertEqual(self.client.get('/api/v1/extracoes_inteligentes').json(),[])

    def test_processamento_legado_idempotente_sem_contexto(self):
        with TemporaryDirectory() as directory, patch.object(settings,'document_storage_path',directory):
            response=self.client.post('/api/v1/contas_consumo/1/documentos/upload',files=dict(file=('conta.pdf',pdf(TEXT),'application/pdf')))
            self.assertEqual(response.status_code,201,response.text)
            document_id=response.json()['id_documento']
            first=self.client.post(f'/api/v1/documentos/{document_id}/processar')
            second=self.client.post(f'/api/v1/documentos/{document_id}/processar')
            self.assertEqual(first.status_code,200,first.text)
            self.assertEqual(second.json(),first.json())
            self.assertEqual(first.json()['extracao']['resultado_validacao_documental'],'EVIDENCIA_INSUFICIENTE')

    def test_contexto_upload_nao_autorizado(self):
        prefix={**ENTITIES[1][2], 'codigo_prefixo':'OUTRO'}
        self.client.post('/api/v1/prefixos',json=prefix)
        response=self.client.post('/api/v1/contas_consumo/1/documentos/upload',
            params=dict(id_usuario=1,id_prefixo=2),files=dict(file=('conta.pdf',pdf(TEXT),'application/pdf')))
        self.assertEqual(response.status_code,403,response.text)

    def test_processar_com_contexto_e_idempotente(self):
        with TemporaryDirectory() as directory, patch.object(settings,'document_storage_path',directory):
            response=self.client.post('/api/v1/contas_consumo/1/documentos/upload',
                params=dict(id_usuario=1),files=dict(file=('conta.pdf',pdf(TEXT),'application/pdf')))
            self.assertEqual(response.status_code,201,response.text)
            document_id=response.json()['id_documento']
            params=dict(id_usuario=1)
            first=self.client.post(f'/api/v1/documentos/{document_id}/processar',params=params)
            second=self.client.post(f'/api/v1/documentos/{document_id}/processar',params=params)
            self.assertEqual(first.status_code,200,first.text)
            self.assertEqual(second.json(),first.json())

    def test_processar_retorna_interpretacao_mais_recente(self):
        first=self.registrar(uf='BA').json()
        second=self.registrar(uf='PE').json()
        response=self.client.post('/api/v1/documentos/1/processar',params=dict(id_usuario=1))
        self.assertEqual(response.status_code,200,response.text)
        self.assertNotEqual(first['id_extracao'],second['id_extracao'])
        self.assertEqual(response.json()['extracao'],second)
