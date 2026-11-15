"""Revisão isolada com autenticação real, SQLite temporário e leitura persistida.
Não conecta ao banco operacional e falha se tentar chamar IA.
"""
import os
os.environ['FRONTEND_ORIGIN'] = 'http://127.0.0.1:5179'
import asyncio
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import uvicorn
from sqlalchemy.orm import Session
from tests.test_auth_demo import DemoAuthTests
from app import models
from app.main import app
from app.core.config import settings

lock = asyncio.Lock()
@app.middleware('http')
async def serialize(request, call_next):
    async with lock:
        return await call_next(request)


case = DemoAuthTests('test_cinco_perfis_com_credenciais_simples')
case.setUp()
storage = TemporaryDirectory()
patch.object(settings, 'document_storage_path', storage.name).start()
patch.object(settings, 'demo_mode', True).start()
patch('app.services.leitura_inteligente.get_document_ai_provider', side_effect=AssertionError('IA proibida na revisão')).start()
id_extracao = case.persisted_extraction()
source = next(Path('backend/storage/documentos').glob('*.pdf'))
shutil.copyfile(source, Path(storage.name) / 'fatura.pdf')
with Session(case.engine) as session:
    e = session.get(models.ExtracaoInteligente, id_extracao)
    e.documento.id_usuario_contexto = e.id_usuario_contexto
    e.documento.caminho_arquivo = 'fatura.pdf'
    e.documento.origem = 'upload'
    e.situacao_validacao = 'pendente'
    session.add(models.DadoExtraido(id_extracao=e.id_extracao, campo_identificado='consumo', valor_extraido='523', valor_validado='523', situacao_validacao='validada'))
    session.commit()
# A fixture remove os overrides de autenticação; get_db mantém apenas o banco isolado.

try:
    uvicorn.run(app, host='127.0.0.1', port=8009, log_level='warning')
finally:
    case.doCleanups()
    storage.cleanup()
