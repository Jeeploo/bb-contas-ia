from app.models.documento import Documento
from app.repositories.documento import DocumentoRepository
from app.repositories.conta_consumo import ContaConsumoRepository
from app.schemas.documento import DocumentoCreate, DocumentoUpdate
from app.services.base import BaseService


class DocumentoService(BaseService[Documento, DocumentoCreate, DocumentoUpdate]):
    repository_class = DocumentoRepository
    foreign_keys = {
        "id_conta": ContaConsumoRepository,
    }
