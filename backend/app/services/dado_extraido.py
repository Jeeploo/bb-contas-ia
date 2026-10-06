from app.models.dado_extraido import DadoExtraido
from app.repositories.dado_extraido import DadoExtraidoRepository
from app.repositories.extracao_inteligente import ExtracaoInteligenteRepository
from app.schemas.dado_extraido import DadoExtraidoCreate, DadoExtraidoUpdate
from app.services.base import BaseService


class DadoExtraidoService(BaseService[DadoExtraido, DadoExtraidoCreate, DadoExtraidoUpdate]):
    repository_class = DadoExtraidoRepository
    foreign_keys = {
        "id_extracao": ExtracaoInteligenteRepository,
    }
