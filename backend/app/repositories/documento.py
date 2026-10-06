from sqlalchemy import select

from app.models.documento import Documento
from app.repositories.base import BaseRepository
from app.schemas.documento import DocumentoCreate, DocumentoUpdate


class DocumentoRepository(
    BaseRepository[Documento, DocumentoCreate, DocumentoUpdate]
):
    model = Documento

    def get_for_processing(self, document_id: int) -> Documento | None:
        return self.session.scalar(select(Documento).where(
            Documento.id_documento == document_id).with_for_update())
