"""Contexto documental protegido pelas dependências de sessão e escopo da API."""
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db, get_contexto_operacional
from app.models import UsuarioPrefixo, ExtracaoInteligente, UnidadeConsumidora
from app.schemas.leitura_documental import ContextoDocumental, LeituraDocumental
from app.schemas.vinculos import UsuarioPrefixosDefinicao, UnidadeConsumidoraCreate, UnidadeConsumidoraRead, UnidadeConsumidoraUpdate
from app.schemas.extracao_inteligente import ExtracaoInteligenteRead
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.interpretacao_documental import InterpretacaoDocumentalService
from app.services.validacao_documental import ValidacaoDocumentalService
from app.services.exceptions import EntityNotFoundError

router = APIRouter(route_class=EntityNotFoundRoute, tags=["Contexto documental"])
DB = Annotated[Session, Depends(get_db)]


@router.put("/usuarios/{id_usuario}/prefixos", response_model=UsuarioPrefixosDefinicao)
def definir_prefixos(id_usuario: int, data: UsuarioPrefixosDefinicao, session: DB):
    ContextoOperacionalService(session).definir(id_usuario, data.vinculos)
    return data


@router.get("/usuarios/{id_usuario}/prefixos", response_model=UsuarioPrefixosDefinicao)
def listar_prefixos(id_usuario: int, session: DB):
    ContextoOperacionalService(session).usuario(id_usuario)
    links = session.scalars(select(UsuarioPrefixo).where(UsuarioPrefixo.id_usuario == id_usuario)).all()
    return {"vinculos": [dict(id_prefixo=l.id_prefixo, ativo=l.ativo, principal=l.principal) for l in links]}


@router.post("/unidades_consumidoras", response_model=UnidadeConsumidoraRead, status_code=201)
def cadastrar_unidade(data: UnidadeConsumidoraCreate, session: DB):
    return ContextoOperacionalService(session).cadastrar_unidade(data)


@router.get("/unidades_consumidoras", response_model=list[UnidadeConsumidoraRead])
def listar_unidades(session: DB):
    query = select(UnidadeConsumidora)
    if 'auth_scope' in session.info:
        query = query.where(UnidadeConsumidora.id_prefixo.in_(session.info['auth_scope'][0]))
    return session.scalars(query).all()


@router.post("/documentos/{id_documento}/interpretacao", response_model=ExtracaoInteligenteRead, status_code=201)
def registrar_interpretacao(id_documento: int, leitura: LeituraDocumental, session: DB, contexto: ContextoDocumental | None = None, operacional=Depends(get_contexto_operacional)):
    contexto = operacional if operacional is not None else contexto
    return InterpretacaoDocumentalService(session).registrar(id_documento, leitura, contexto)


@router.post("/extracoes_inteligentes/{id_extracao}/enviar-validacao", response_model=ExtracaoInteligenteRead)
@router.post("/extracoes_inteligentes/{id_extracao}/revalidar", response_model=ExtracaoInteligenteRead)
def revalidar(id_extracao: int, session: DB, request: Request, contexto: ContextoDocumental | None = None, operacional=Depends(get_contexto_operacional)):
    contexto = operacional if operacional is not None else contexto
    try:
        extraction = session.scalar(select(ExtracaoInteligente).where(
            ExtracaoInteligente.id_extracao == id_extracao).with_for_update())
        if extraction is None:
            raise EntityNotFoundError("ExtracaoInteligente", id_extracao)
        if request.url.path.endswith("/enviar-validacao"):
            from app.services.validacao_documental import encaminhar_revisao
            encaminhar_revisao(session, extraction, contexto)
        else:
            ValidacaoDocumentalService(session).revalidar(extraction, contexto)
        from app.services.conta_consumo import ContaConsumoService
        ContaConsumoService(session).criar_da_leitura(extraction)
        session.commit()
        return extraction
    except Exception:
        session.rollback()
        raise


@router.patch("/unidades_consumidoras/{id_unidade}", response_model=UnidadeConsumidoraRead)
def atualizar_unidade(id_unidade: int, data: UnidadeConsumidoraUpdate, session: DB):
    return ContextoOperacionalService(session).atualizar_unidade(id_unidade, data)


from pydantic import BaseModel, ConfigDict


class ResolverConcessionaria(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_concessionaria: int


@router.post("/extracoes_inteligentes/{id_extracao}/resolver-concessionaria", response_model=ExtracaoInteligenteRead)
def resolver_concessionaria(id_extracao: int, data: ResolverConcessionaria, session: DB,
                            contexto=Depends(get_contexto_operacional)):
    from app.services.correspondencia_concessionaria import associar
    from fastapi import HTTPException
    if contexto is None:
        raise HTTPException(401, "Sessão obrigatória")
    try:
        extraction = session.scalar(select(ExtracaoInteligente).where(
            ExtracaoInteligente.id_extracao == id_extracao).with_for_update())
        if extraction is None:
            raise EntityNotFoundError("ExtracaoInteligente", id_extracao)
        result = associar(session, extraction, data.id_concessionaria, contexto)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
