from sqlalchemy import select
from pydantic import ValidationError
from app.models.perfil_processamento import PerfilProcessamento
from app.models.prefixo import Prefixo
from app.repositories.perfil_processamento import PerfilProcessamentoRepository
from app.repositories.prefixo import PrefixoRepository
from app.repositories.regra_calculo import RegraCalculoRepository
from app.repositories.concessionaria import ConcessionariaRepository
from app.schemas.perfil_processamento import PerfilProcessamentoCreate, PerfilProcessamentoUpdate
from app.services.base import BaseService
from app.services.exceptions import CalculationError


class PerfilProcessamentoService(BaseService[PerfilProcessamento, PerfilProcessamentoCreate, PerfilProcessamentoUpdate]):
    repository_class = PerfilProcessamentoRepository
    foreign_keys = {"id_prefixo": PrefixoRepository, "id_regra": RegraCalculoRepository}

    def _validate_foreign_keys(self, data):
        super()._validate_foreign_keys(data)
        if data.id_concessionaria is not None and ConcessionariaRepository(self.session).get_by_id(data.id_concessionaria) is None:
            raise CalculationError("Concessionária esperada inexistente")
        # Serializa a configuração de perfis do mesmo Prefixo no PostgreSQL.
        self.session.scalars(select(Prefixo).where(Prefixo.id_prefixo == data.id_prefixo).with_for_update()).first()
        if data.situacao == "ativo":
            for other in self.session.scalars(select(PerfilProcessamento).where(
                    PerfilProcessamento.id_prefixo == data.id_prefixo,
                    PerfilProcessamento.situacao == "ativo")).all():
                if other.id_perfil == getattr(self, "_updating_id", None):
                    continue
                if (data.data_fim_vigencia is None or other.data_inicio_vigencia <= data.data_fim_vigencia) and (other.data_fim_vigencia is None or data.data_inicio_vigencia <= other.data_fim_vigencia):
                    raise CalculationError("Perfil ativo com vigência sobreposta para o Prefixo")

    def update(self, entity_id, data):
        current = self.get_by_id(entity_id)
        try:
            merged = PerfilProcessamentoCreate.model_validate({
                **{key: getattr(current, key) for key in PerfilProcessamentoCreate.model_fields},
                **data.model_dump(exclude_unset=True)})
        except ValidationError as exc:
            raise CalculationError(str(exc)) from exc
        self._updating_id = entity_id
        try:
            return super().update(entity_id, merged)
        finally:
            self._updating_id = None
