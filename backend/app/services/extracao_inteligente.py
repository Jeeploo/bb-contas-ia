from app.models.extracao_inteligente import ExtracaoInteligente
from app.repositories.extracao_inteligente import ExtracaoInteligenteRepository
from app.repositories.documento import DocumentoRepository
from app.schemas.extracao_inteligente import ExtracaoInteligenteCreate, ExtracaoInteligenteUpdate
from app.services.base import BaseService


class ExtracaoInteligenteService(BaseService[ExtracaoInteligente, ExtracaoInteligenteCreate, ExtracaoInteligenteUpdate]):
    revalida_contexto_documental = True
    repository_class = ExtracaoInteligenteRepository
    foreign_keys = {
        "id_documento": DocumentoRepository,
    }
