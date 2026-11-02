from typing import Literal
from pydantic import BaseModel
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api import EntityNotFoundRoute
from app.api.dependencies import get_db, get_contexto_operacional
from app.schemas.leitura_inteligente import ProcessamentoInteligenteRead, TentativasLeituraRead
from app.schemas.processamento_documento import ProcessamentoDocumentoRead
from app.services.processamento_documento import ProcessamentoDocumentoService
from app.schemas.documento import DocumentoCreate, DocumentoRead, DocumentoUpdate
from app.services.documento import DocumentoService


router = APIRouter(
    prefix="/documentos", tags=["Documento"], route_class=EntityNotFoundRoute
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=DocumentoRead, status_code=status.HTTP_201_CREATED)
def create(data: DocumentoCreate, session: DatabaseSession):
    return DocumentoService(session).create(data)


@router.get("", response_model=list[DocumentoRead])
def list_entities(
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 100,
):
    return DocumentoService(session).list(offset=offset, limit=limit)


@router.post("/upload", response_model=DocumentoRead, status_code=201)
def upload_inicial(session: DatabaseSession, file: UploadFile, contexto=Depends(get_contexto_operacional)):
    return ProcessamentoDocumentoService(session).upload_inicial(
        file.file, file.filename or "", file.content_type or "", contexto)


class JornadaRead(BaseModel):
    documento: DocumentoRead | None
    processamento: ProcessamentoInteligenteRead | None
    calculo: dict | None


class DecisaoChecker(BaseModel):
    decisao: Literal['aprovado', 'rejeitado']
    observacao: str = ''


@router.get('/jornada/atual', response_model=JornadaRead)
def retomar_jornada(session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    from app.services.jornada_demo import JornadaDemoService
    return JornadaDemoService(session).retomar(contexto)


@router.get('/jornada/checker', response_model=list[JornadaRead])
def fila_checker(session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    from app.services.jornada_demo import JornadaDemoService
    return JornadaDemoService(session).fila(contexto)


@router.get('/{id_documento}/jornada', response_model=JornadaRead)
def jornada_documento(id_documento: int, session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    from app.services.jornada_demo import JornadaDemoService
    service = JornadaDemoService(session)
    document, extraction, _ = service.obter(id_documento, contexto)
    return service.resposta(document, extraction)


@router.post('/{id_documento}/calcular-demo')
def calcular_demo(id_documento: int, session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    from app.services.jornada_demo import JornadaDemoService
    return JornadaDemoService(session).calcular(id_documento, contexto)


@router.post('/{id_documento}/nova-fatura', status_code=204)
def nova_fatura(id_documento: int, session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    from app.services.jornada_demo import JornadaDemoService
    JornadaDemoService(session).nova(id_documento, contexto)
    return Response(status_code=204)


@router.post('/{id_documento}/decisao-checker', response_model=JornadaRead)
def decidir_checker(id_documento: int, data: DecisaoChecker, session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    from app.services.jornada_demo import JornadaDemoService
    return JornadaDemoService(session).decidir(id_documento, contexto, data.decisao, data.observacao)


@router.get('/{id_documento}/arquivo')
def arquivo_documento(id_documento: int, session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    from app.services.jornada_demo import JornadaDemoService
    from app.processing.storage import storage_for_document, document_storage_key
    document, _, _ = JornadaDemoService(session).obter(id_documento, contexto)
    mime = {'pdf': 'application/pdf', 'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}.get(document.formato, 'application/octet-stream')
    return Response(storage_for_document(document).read(document_storage_key(document)), media_type=mime,
        headers={'Cache-Control': 'private, no-store', 'Content-Disposition': f'inline; filename="fatura-{document.id_documento}.{document.formato}"'})


@router.get("/{id}", response_model=DocumentoRead)
def get_by_id(id: int, session: DatabaseSession):
    return DocumentoService(session).get_by_id(id)


@router.patch("/{id}", response_model=DocumentoRead)
def update(id: int, data: DocumentoUpdate, session: DatabaseSession):
    return DocumentoService(session).update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(id: int, session: DatabaseSession):
    DocumentoService(session).delete(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id_documento}/processar", response_model=ProcessamentoDocumentoRead)
def processar(id_documento: int, session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    return ProcessamentoDocumentoService(session).processar(id_documento, contexto)


@router.post("/{id_documento}/processar-inteligente", response_model=ProcessamentoInteligenteRead)
def processar_inteligente(id_documento: int, session: DatabaseSession,
                          reprocessar: bool = False, contexto=Depends(get_contexto_operacional)):
    return ProcessamentoDocumentoService(session).processar_inteligente(
        id_documento, contexto, reprocessar=reprocessar)


@router.get("/{id_documento}/leituras-ia", response_model=TentativasLeituraRead)
def tentativas_ia(id_documento: int, session: DatabaseSession, contexto=Depends(get_contexto_operacional)):
    from app.services.contexto_operacional import ContextoOperacionalService
    from app.services.exceptions import ContextoOperacionalError
    document = DocumentoService(session).get_by_id(id_documento)
    if contexto is None:
        raise ContextoOperacionalError('Consulta exige contexto de usuário')
    prefix = ContextoOperacionalService(session).resolver(contexto.id_usuario, contexto.id_prefixo)
    if prefix.id_prefixo != (document.conta.id_prefixo if document.conta else document.id_prefixo_contexto):
        raise ContextoOperacionalError('Prefixo não autorizado para a conta')
    return {'tentativas': document.historico_leitura_ia}
