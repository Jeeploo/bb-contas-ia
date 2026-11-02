"""Sessão obrigatória e autorização por vínculo; identidade não vem do cliente."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, inspect
from sqlalchemy.orm import Session
from app.api.db_dependency import get_db
from app.core.config import settings
from app.models import Usuario
from app.models.auth_demo import CredencialDemo, SessaoDemo
from app.services.auth_demo import COOKIE, now, token_hash
from app.services.contexto_operacional import ContextoOperacionalService


def check_origin(request):
    origin = request.headers.get('origin')
    if origin and origin not in settings.allowed_origins:
        raise HTTPException(403, 'Origem não autorizada.')


def get_demo_session(request: Request, session: Session = Depends(get_db)):
    if not settings.demo_auth_enabled:
        raise HTTPException(503, 'Autenticação DEMO não habilitada neste ambiente.')
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        check_origin(request)
    token = request.cookies.get(COOKIE, '')
    auth = session.get(SessaoDemo, token_hash(token)) if 20 <= len(token) <= 200 else None
    if auth is None or auth.expira_em <= now():
        raise HTTPException(401, 'Sessão ausente ou expirada. Entre novamente.')
    return auth


def get_current_user(auth=Depends(get_demo_session), session: Session = Depends(get_db)):
    user = session.get(Usuario, auth.id_usuario)
    if user is None or user.situacao != 'ativo' or session.get(CredencialDemo, user.id_usuario) is None:
        raise HTTPException(401, 'Sessão inválida. Entre novamente.')
    return user


def scope_expression(model, ids, user_id):
    from app.models import (Prefixo, ContaConsumo, Documento, ExtracaoInteligente, DadoExtraido,
        ItemExtraido, Calculo, OrdemPagamento, ItemPagamento, Aprovacao, PerfilProcessamento, UnidadeConsumidora)
    account = ContaConsumo.id_prefixo.in_(ids)
    document = Documento.conta.has(account) | ((Documento.id_conta.is_(None)) & Documento.id_prefixo_contexto.in_(ids))
    extraction = ExtracaoInteligente.documento.has(document)
    calculation = Calculo.conta.has(account)
    order = OrdemPagamento.calculo.has(calculation)
    expressions = {Prefixo: Prefixo.id_prefixo.in_(ids), Usuario: Usuario.id_usuario == user_id,
        ContaConsumo: account, Documento: document, ExtracaoInteligente: extraction,
        DadoExtraido: DadoExtraido.extracao.has(extraction), ItemExtraido: ItemExtraido.extracao.has(extraction),
        Calculo: calculation, OrdemPagamento: order, ItemPagamento: ItemPagamento.ordem.has(order),
        Aprovacao: Aprovacao.ordem.has(order), PerfilProcessamento: PerfilProcessamento.id_prefixo.in_(ids),
        UnidadeConsumidora: UnidadeConsumidora.id_prefixo.in_(ids)}
    return expressions.get(model)


async def authorize_request(request: Request, user=Depends(get_current_user), session: Session = Depends(get_db)):
    """Além do login, bloqueia cadastros administrativos e acessos por ID externo."""
    from app import models
    ids = [p.id_prefixo for p in ContextoOperacionalService(session).ativos(user.id_usuario)]
    if not ids:
        raise HTTPException(403, 'Usuário sem prefixo ativo autorizado.')
    session.info['auth_scope'] = (ids, user.id_usuario)
    parts = request.url.path.removeprefix('/api/v1/').split('/')
    # Cadastro não pode permitir que um usuário DEMO amplie a própria alçada/vínculos.
    allowed = request.method == 'GET' or (
        request.method == 'POST' and (
            parts == ['documentos', 'upload'] or parts in [['ordens_pagamento'], ['aprovacoes']]
            or (len(parts) == 3 and (
                parts[0] == 'documentos' and parts[2] in {'processar', 'processar-inteligente', 'interpretacao'}
                or parts[0] == 'contas_consumo' and parts[2] == 'calcular'
                or parts[0] == 'extracoes_inteligentes' and parts[2] in {'revalidar', 'enviar-validacao'}))
            or len(parts) == 4 and parts[0] == 'contas_consumo' and parts[2:] == ['documentos', 'upload'])
    ) or (request.method == 'PATCH' and len(parts) == 3 and parts[0] in {'dados_extraidos', 'itens_extraidos'} and parts[2] == 'validacao')
    if not allowed:
        raise HTTPException(403, 'Cadastro administrativo indisponível no acesso DEMO.')
    table_models = {m.local_table.name: m.class_ for m in models.Base.registry.mappers}
    model = table_models.get(parts[0])
    def ensure(model, key):
        clause = scope_expression(model, ids, user.id_usuario)
        pk = inspect(model).primary_key[0]
        if clause is not None and session.scalar(select(model).where(pk == key, clause)) is None:
            raise HTTPException(404, 'Registro não encontrado no contexto autorizado.')
    if model is not None and len(parts) > 1 and parts[1].isdigit():
        ensure(model, int(parts[1]))
    media_type = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
    if request.method in {'POST', 'PATCH'} and (media_type == 'application/json' or media_type.endswith('+json')):
        body = await request.json()
        if isinstance(body, dict):
            for name in ('id_usuario', 'id_usuario_criador'):
                if name in body and body[name] != user.id_usuario:
                    raise HTTPException(403, 'Identidade deve corresponder à sessão autenticada.')
            for name, target in [('id_calculo', models.Calculo), ('id_ordem', models.OrdemPagamento)]:
                if name in body:
                    ensure(target, body[name])
            context = body.get('contexto', body if parts[-1] == 'revalidar' else None)
            if isinstance(context, dict):
                if 'id_usuario' in context and context['id_usuario'] != user.id_usuario:
                    raise HTTPException(403, 'Identidade deve corresponder à sessão autenticada.')
                if context.get('id_prefixo') is not None and context['id_prefixo'] not in ids:
                    raise HTTPException(403, 'Prefixo não autorizado.')
    requested_user = request.query_params.get('id_usuario')
    if requested_user is not None and requested_user != str(user.id_usuario):
        raise HTTPException(403, 'Identidade deve corresponder à sessão autenticada.')
    requested_prefix = request.query_params.get('id_prefixo')
    if requested_prefix is not None and requested_prefix not in {str(i) for i in ids}:
        raise HTTPException(403, 'Prefixo não autorizado.')
