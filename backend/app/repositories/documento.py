from app.models.documento import Documento
from app.repositories.base import BaseRepository
from app.schemas.documento import DocumentoCreate, DocumentoUpdate


class DocumentoRepository(
    BaseRepository[Documento, DocumentoCreate, DocumentoUpdate]
):
    model = Documento
