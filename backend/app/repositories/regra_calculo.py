from app.models.regra_calculo import RegraCalculo
from app.repositories.base import BaseRepository
from app.schemas.regra_calculo import RegraCalculoCreate, RegraCalculoUpdate


class RegraCalculoRepository(
    BaseRepository[RegraCalculo, RegraCalculoCreate, RegraCalculoUpdate]
):
    model = RegraCalculo
