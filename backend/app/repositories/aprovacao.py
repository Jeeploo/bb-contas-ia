from app.models.aprovacao import Aprovacao
from app.repositories.base import BaseRepository
from app.schemas.aprovacao import AprovacaoCreate, AprovacaoUpdate


class AprovacaoRepository(BaseRepository[Aprovacao, AprovacaoCreate, AprovacaoUpdate]):
    model = Aprovacao
