"""Servidor isolado de revisão: SQLite temporário e replay de leitura persistida, sem IA.

PYTHONPATH=backend backend/.venv/bin/python frontend/review/journey-server.py /tmp/bb-jornada-real.json
Não conecta ao banco operacional. A autenticação é substituída apenas neste servidor de teste.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from fastapi import Request
import uvicorn
from tests.test_documento_inicial import DocumentoInicialTests
from app.main import app
from app.api.dependencies import get_contexto_operacional
from app.schemas.leitura_documental import ContextoDocumental, LeituraDocumental
from app.services.interpretacao_documental import COMPONENTES
from app.document_ai.base import InterpretacaoAI
from app.document_ai.normalizacao import normalizar_leitura
from sqlalchemy.orm import Session
from app.services.regra_demo import configurar_regra_demo
from app.models import Localidade

review_lock = asyncio.Lock()
@app.middleware('http')
async def serialize_sqlite_review(request, call_next):
    # StaticPool compartilha uma conexão; React StrictMode pode consultar em paralelo.
    async with review_lock:
        response = await call_next(request)
        if request.url.path.endswith('/processar-inteligente') and response.status_code == 200:
            document_id = int(request.url.path.split('/')[-2])
            with Session(case.engine) as session, session.begin():
                configurar_regra_demo(session, document_id)
        return response

snapshot = json.loads(Path(sys.argv[1]).read_text())
case = DocumentoInicialTests('test_cria_conta_da_leitura_idempotente')
case.setUp()
original = {}
for field in snapshot['campos_encontrados']:
    key = {'valor_original': 'valor_total'}.get(field['campo_identificado'], field['campo_identificado'])
    if key in LeituraDocumental.model_fields:
        original[key] = field.get('valor_normalizado') or field['valor_extraido']
for item in snapshot['itens_encontrados']:
    key = next((k for k, v in COMPONENTES.items() if v == item['tipo_normalizado']), None)
    if key:
        original[key] = item['valor']
case.provider.interpretar_documento.return_value = InterpretacaoAI(normalizar_leitura(original), original, dict(status='concluida', provider='replay_persistido'))
# Somente o banco isolado recebe o contexto territorial documental e a regra explícita de teste.
with case.engine.begin() as connection:
    connection.execute(Localidade.__table__.update().values(municipio=original['municipio'], estado=original['uf']))
for resource, payload in [
    ('alcadas',dict(nome_nivel='Checker teste',limite_financeiro='100000',data_inicio_vigencia='2020-01-01')),
    ('usuarios',dict(matricula='CHECKER-TESTE',nome='Checker teste',funcao='checker',situacao='ativo',id_prefixo=1,id_alcada=1)),
]:
    response=case.client.post('/api/v1/'+resource,json=payload)
    assert response.status_code == 201, response.text

def context(request: Request):
    return ContextoDocumental(id_usuario=int(request.headers.get('x-review-user','1')),id_prefixo=1)
app.dependency_overrides[get_contexto_operacional] = context

@app.get('/review/stats')
def stats():
    return dict(replays=case.provider.interpretar_documento.call_count, chamadas_ia=0)

Path(f"/tmp/bb-jornada-review-{os.environ.get('REVIEW_PORT','8007')}.pid").write_text(str(os.getpid()))
try:
    uvicorn.run(app,host='127.0.0.1',port=int(os.environ.get('REVIEW_PORT','8007')),log_level='warning')
finally:
    case.doCleanups()
