from app.models.item_extraido import ItemExtraido
from app.repositories.item_extraido import ItemExtraidoRepository
from app.schemas.item_extraido import ItemExtraidoCreate, ItemExtraidoValidacao
from app.services.base import BaseService
from app.services.exceptions import CalculationError


class ItemExtraidoService(BaseService[ItemExtraido, ItemExtraidoCreate, ItemExtraidoValidacao]):
    repository_class = ItemExtraidoRepository

    def validar(self, entity_id, data):
        try:
            item = self.get_by_id(entity_id)
            value = data.valor_validado if "valor_validado" in data.model_fields_set else item.valor
            if value is None or value < 0:
                raise CalculationError("Componente deve ter magnitude não negativa; desconto é definido pela regra")
            item.valor_validado = value
            item.situacao_validacao = "validada"
            self.session.flush()
            self.session.commit()
            return item
        except Exception:
            self.session.rollback()
            raise
