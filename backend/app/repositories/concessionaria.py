from app.models.concessionaria import Concessionaria
from app.repositories.base import BaseRepository
from app.schemas.concessionaria import ConcessionariaCreate, ConcessionariaUpdate


class ConcessionariaRepository(
    BaseRepository[Concessionaria, ConcessionariaCreate, ConcessionariaUpdate]
):
    model = Concessionaria
