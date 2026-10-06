from sqlalchemy import select

from app.models.extracao_inteligente import ExtracaoInteligente
from app.repositories.base import BaseRepository
from app.schemas.extracao_inteligente import ExtracaoInteligenteCreate, ExtracaoInteligenteUpdate


class ExtracaoInteligenteRepository(
    BaseRepository[ExtracaoInteligente, ExtracaoInteligenteCreate, ExtracaoInteligenteUpdate]
):
    model = ExtracaoInteligente

    def get_completed_for_document(self, document_id: int) -> ExtracaoInteligente | None:
        return self.session.scalars(select(ExtracaoInteligente).where(
            ExtracaoInteligente.id_documento == document_id,
            ExtracaoInteligente.situacao_validacao.in_(
                ("processada", "requer_validacao", "validada", "pendente")),
        ).order_by(ExtracaoInteligente.id_extracao)).first()
