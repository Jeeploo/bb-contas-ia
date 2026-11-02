"""Revisão HTTP autenticada com dados COMPESA informados, SQLite isolado e IA proibida."""
import asyncio
from unittest.mock import patch
import uvicorn
from sqlalchemy.orm import Session
from tests.test_auth_demo import DemoAuthTests
from app.main import app
from app import models
from app.core.config import settings
from app.services.validacao_documental import ValidacaoDocumentalService

lock = asyncio.Lock()
@app.middleware('http')
async def serialized(request, call_next):
    async with lock:
        return await call_next(request)

case = DemoAuthTests('test_confirmar_jornada_autenticada_cadastro_opcional_agua_e_energia')
case.setUp()
settings.demo_mode = True
extraction_id = case.persisted_extraction()
with Session(case.engine) as session:
    e = session.get(models.ExtracaoInteligente, extraction_id)
    e.documento.id_usuario_contexto = e.id_usuario_contexto
    e.documento.formato = 'png'
    e.situacao_validacao = 'requer_validacao'
    session.get(models.Prefixo, e.id_prefixo_contexto).localidade.municipio = 'Paulista'
    values = dict(tipo_documento='AGUA', uf='PE', municipio='Paulista',
        concessionaria='COMPANHIA PERNAMBUCANA DE SANEAMENTO', unidade_consumidora='SEM-VINCULO-COMPESA',
        competencia='2026-08', data_vencimento='2026-09-15', valor_original='92.66', consumo='8', unidade_consumo='m³')
    for field in list(e.dados_extraidos):
        session.delete(field)
    session.flush()
    for name, value in values.items():
        session.add(models.DadoExtraido(id_extracao=e.id_extracao, campo_identificado=name,
            valor_extraido=value, valor_normalizado=value, situacao_validacao='pendente'))
    session.flush()
    session.expire(e, ['dados_extraidos'])
    ValidacaoDocumentalService(session).revalidar(e)
    session.commit()
try:
    with patch('app.services.leitura_inteligente.get_document_ai_provider', side_effect=AssertionError('IA proibida')):
        uvicorn.run(app, host='127.0.0.1', port=8008, log_level='warning')
finally:
    case.doCleanups()
