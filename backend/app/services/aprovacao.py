from app.models.aprovacao import Aprovacao
from app.repositories.alcada import AlcadaRepository
from app.repositories.aprovacao import AprovacaoRepository
from app.repositories.ordem_pagamento import OrdemPagamentoRepository
from app.repositories.usuario import UsuarioRepository
from app.schemas.aprovacao import AprovacaoCreate, AprovacaoUpdate
from app.schemas.ordem_pagamento import OrdemPagamentoUpdate
from app.services.base import BaseService
from app.services.exceptions import (
    ApprovalOrderChangeNotAllowedError,
    EntityNotFoundError,
    InsufficientApprovalLimitError,
    SelfApprovalNotAllowedError,
)


class AprovacaoService(BaseService[Aprovacao, AprovacaoCreate, AprovacaoUpdate]):
    repository_class = AprovacaoRepository
    foreign_keys = {
        "id_ordem": OrdemPagamentoRepository,
        "id_usuario": UsuarioRepository,
    }

    def _validate_decision(
        self, id_ordem: int | None, id_usuario: int | None, decisao: str | None
    ) -> str | None:
        ordem = OrdemPagamentoRepository(self.session).get_by_id(id_ordem) if id_ordem is not None else None
        if ordem is None:
            raise EntityNotFoundError("OrdemPagamento", id_ordem)
        usuario = UsuarioRepository(self.session).get_by_id(id_usuario) if id_usuario is not None else None
        if usuario is None:
            raise EntityNotFoundError("Usuario", id_usuario)
        if ordem.id_usuario_criador == usuario.id_usuario:
            raise SelfApprovalNotAllowedError("O criador não pode decidir sobre a própria ordem")
        decision = decisao.strip().lower() if decisao is not None else None
        if decision == "aprovado":
            if usuario.id_alcada is None:
                raise InsufficientApprovalLimitError("Usuário sem alçada financeira para aprovar")
            alcada = AlcadaRepository(self.session).get_by_id(usuario.id_alcada)
            if alcada is None:
                raise EntityNotFoundError("Alcada", usuario.id_alcada)
            if alcada.limite_financeiro < ordem.valor_total:
                raise InsufficientApprovalLimitError("Alçada financeira inferior ao valor da ordem")
        return decision

    def _update_order(self, id_ordem: int, decision: str | None) -> None:
        situacao = {"aprovado": "aprovada", "rejeitado": "rejeitada"}.get(decision)
        if situacao is not None:
            ordem = OrdemPagamentoRepository(self.session).update(
                id_ordem, OrdemPagamentoUpdate(situacao=situacao)
            )
            if ordem is None:
                raise EntityNotFoundError("OrdemPagamento", id_ordem)

    def create(self, data: AprovacaoCreate) -> Aprovacao:
        try:
            decision = self._validate_decision(data.id_ordem, data.id_usuario, data.decisao)
            instance = self.repository.create(data)
            self._update_order(data.id_ordem, decision)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return instance

    def update(self, entity_id: int, data: AprovacaoUpdate) -> Aprovacao:
        """Revalida o estado final; o vínculo com a ordem é imutável no MVP."""
        try:
            current = self.get_by_id(entity_id)
            values = data.model_dump(exclude_unset=True)
            id_ordem = values.get("id_ordem", current.id_ordem)
            id_usuario = values.get("id_usuario", current.id_usuario)
            decision = self._validate_decision(
                id_ordem, id_usuario, values.get("decisao", current.decisao)
            )
            if id_ordem != current.id_ordem:
                raise ApprovalOrderChangeNotAllowedError("Não é permitido transferir uma aprovação para outra ordem")
            instance = self.repository.update(entity_id, data)
            if instance is None:
                raise EntityNotFoundError("Aprovacao", entity_id)
            self._update_order(id_ordem, decision)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return instance
