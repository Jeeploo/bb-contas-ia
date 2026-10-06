from app.models.perfil_processamento import PerfilProcessamento
from app.schemas.perfil_processamento import PerfilProcessamentoCreate, PerfilProcessamentoUpdate
from app.repositories.base import BaseRepository


class PerfilProcessamentoRepository(BaseRepository[PerfilProcessamento, PerfilProcessamentoCreate, PerfilProcessamentoUpdate]):
    model = PerfilProcessamento
