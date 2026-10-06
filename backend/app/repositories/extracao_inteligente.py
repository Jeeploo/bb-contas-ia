from app.models.extracao_inteligente import ExtracaoInteligente
from app.repositories.base import BaseRepository
from app.schemas.extracao_inteligente import ExtracaoInteligenteCreate, ExtracaoInteligenteUpdate


class ExtracaoInteligenteRepository(
    BaseRepository[ExtracaoInteligente, ExtracaoInteligenteCreate, ExtracaoInteligenteUpdate]
):
    model = ExtracaoInteligente
