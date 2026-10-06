from app.models.prefixo import Prefixo
from app.repositories.base import BaseRepository
from app.schemas.prefixo import PrefixoCreate, PrefixoUpdate


class PrefixoRepository(
    BaseRepository[Prefixo, PrefixoCreate, PrefixoUpdate]
):
    model = Prefixo
