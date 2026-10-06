from app.models.dado_extraido import DadoExtraido
from app.repositories.dado_extraido import DadoExtraidoRepository
from app.repositories.extracao_inteligente import ExtracaoInteligenteRepository
from app.schemas.dado_extraido import DadoExtraidoCreate, DadoExtraidoUpdate, DadoExtraidoValidacao
from app.services.base import BaseService


class DadoExtraidoService(BaseService[DadoExtraido, DadoExtraidoCreate, DadoExtraidoUpdate]):
    repository_class = DadoExtraidoRepository
    foreign_keys = {
        "id_extracao": ExtracaoInteligenteRepository,
    }

    def validar(self, entity_id: int, data: DadoExtraidoValidacao) -> DadoExtraido:
        try:
            instance = self.get_by_id(entity_id)
            instance.valor_validado = (data.valor_validado if "valor_validado" in data.model_fields_set
                                      else instance.valor_extraido)
            instance.situacao_validacao = "validada"
            self.session.flush()
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return instance
