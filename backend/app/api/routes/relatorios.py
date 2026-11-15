"""Consultas gerenciais da jornada, limitadas ao prefixo autorizado."""
from datetime import date
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db, get_contexto_operacional
from app.models import ExtracaoInteligente, Usuario
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.jornada_demo import evento

router = APIRouter(tags=['Relatórios'], route_class=EntityNotFoundRoute)


def aprovadas(session, contexto, id_prefixo=None, tipo=None, data_inicio=None, data_fim=None):
    prefix = ContextoOperacionalService(session).resolver(contexto.id_usuario, id_prefixo if id_prefixo is not None else contexto.id_prefixo)
    rows = []
    extractions = session.scalars(select(ExtracaoInteligente).where(
        ExtracaoInteligente.id_prefixo_contexto == prefix.id_prefixo,
        ExtracaoInteligente.situacao_validacao == 'confirmada_checker'))
    for e in extractions:
        decision, calc = evento(e, 'DECISAO_CHECKER'), evento(e, 'CALCULO_DEMO')
        if not decision or decision.get('decisao') != 'aprovado' or not calc:
            continue
        fields = {f.campo_identificado: f.valor_validado or f.valor_normalizado or f.valor_extraido for f in e.dados_extraidos}
        category = 'energia' if 'ENERGIA' in str(fields.get('tipo_documento', '')).upper() else 'agua'
        month = fields.get('competencia', '')
        if tipo and category != tipo or data_inicio and month < data_inicio.strftime('%Y-%m') or data_fim and month > data_fim.strftime('%Y-%m'):
            continue
        maker = session.get(Usuario, e.documento.id_usuario_contexto)
        checker = session.get(Usuario, decision['id_usuario'])
        rows.append(dict(id_fatura=e.id_documento, tipo=category, competencia=month,
            id_prefixo=prefix.id_prefixo, prefixo=prefix.codigo_prefixo,
            valor=calc['calculo']['valor_calculado'], consumo=fields.get('consumo') or '0',
            solicitado_por=maker.nome if maker else '', confirmado_por=checker.nome if checker else '',
            data_confirmacao=decision['data']))
    return sorted(rows, key=lambda r: r['data_confirmacao'], reverse=True)


@router.get('/faturas')
def faturas(session=Depends(get_db), contexto=Depends(get_contexto_operacional)):
    return aprovadas(session, contexto)


@router.get('/relatorios/resumo')
def resumo(id_prefixo: int | None = None, tipo: Literal['agua', 'energia'] | None = None,
           data_inicio: date | None = None, data_fim: date | None = None,
           session=Depends(get_db), contexto=Depends(get_contexto_operacional)):
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(422, 'O início do período deve ser anterior ao fim')
    rows = aprovadas(session, contexto, id_prefixo, tipo, data_inicio, data_fim)
    monthly, prefixes = {}, {}
    total = Decimal(0)
    energy = water = Decimal(0)
    for r in rows:
        value, consumption = Decimal(r['valor']), Decimal(r['consumo'])
        total += value
        if r['tipo'] == 'energia': energy += consumption
        else: water += consumption
        bucket = monthly.setdefault(r['competencia'], dict(competencia=r['competencia'], valor=Decimal(0), energia=Decimal(0), agua=Decimal(0)))
        bucket['valor'] += value
        bucket[r['tipo']] += consumption
        prefixes[r['prefixo']] = prefixes.get(r['prefixo'], Decimal(0)) + value
    return dict(valor_total=total, quantidade=len(rows), energia=energy, agua=water,
                mensal=[monthly[k] for k in sorted(monthly)], prefixos=[dict(prefixo=k, valor=v) for k,v in prefixes.items()])
