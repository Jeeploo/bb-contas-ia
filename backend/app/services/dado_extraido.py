from app.models.dado_extraido import DadoExtraido
from app.repositories.dado_extraido import DadoExtraidoRepository
from app.repositories.extracao_inteligente import ExtracaoInteligenteRepository
from app.schemas.dado_extraido import DadoExtraidoCreate, DadoExtraidoUpdate, DadoExtraidoValidacao
from app.services.base import BaseService


class DadoExtraidoService(BaseService[DadoExtraido, DadoExtraidoCreate, DadoExtraidoUpdate]):
    revalida_contexto_documental = True
    repository_class = DadoExtraidoRepository
    foreign_keys = {
        "id_extracao": ExtracaoInteligenteRepository,
    }

    def _validate_update(self, instance, data):
        protected = {"valor_extraido", "campo_identificado", "id_extracao"}
        if (instance.situacao_validacao == "validada" or instance.valor_validado is not None) and protected.intersection(data.model_fields_set):
            from app.services.exceptions import ContextoOperacionalError
            raise ContextoOperacionalError("Original revisado é imutável; use a validação humana")

    def validar(self, entity_id: int, data: DadoExtraidoValidacao) -> DadoExtraido:
        try:
            instance = self.get_by_id(entity_id)
            from sqlalchemy import select
            from app.models.extracao_inteligente import ExtracaoInteligente
            self.session.scalar(select(ExtracaoInteligente).where(
                ExtracaoInteligente.id_extracao == instance.id_extracao).with_for_update())
            instance.valor_validado = (data.valor_validado if "valor_validado" in data.model_fields_set
                                      else (instance.valor_normalizado if instance.valor_normalizado is not None else instance.valor_extraido))
            instance.situacao_validacao = "validada"
            self.session.flush()
            from app.services.validacao_documental import ValidacaoDocumentalService
            if instance.campo_identificado in {"tipo_documento", "uf", "municipio", "concessionaria", "unidade_consumidora", "endereco_unidade"}:
                ValidacaoDocumentalService(self.session).revalidar(instance.extracao)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return instance
