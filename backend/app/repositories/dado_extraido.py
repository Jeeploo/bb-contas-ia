from app.models.dado_extraido import DadoExtraido
from app.repositories.base import BaseRepository
from app.schemas.dado_extraido import DadoExtraidoCreate, DadoExtraidoUpdate


class DadoExtraidoRepository(
    BaseRepository[DadoExtraido, DadoExtraidoCreate, DadoExtraidoUpdate]
):
    model = DadoExtraido
