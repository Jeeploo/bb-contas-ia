from app.models.prefixo import Prefixo
from app.repositories.prefixo import PrefixoRepository
from app.repositories.localidade import LocalidadeRepository
from app.schemas.prefixo import PrefixoCreate, PrefixoUpdate
from app.services.base import BaseService


class PrefixoService(BaseService[Prefixo, PrefixoCreate, PrefixoUpdate]):
    revalida_contexto_documental = True
    repository_class = PrefixoRepository
    foreign_keys = {
        "id_localidade": LocalidadeRepository,
    }

    def _validate_update(self, instance, data):
        if "situacao" not in data.model_fields_set or data.situacao == "ativo":
            return
        prefix_id = instance.id_prefixo
        from sqlalchemy import select
        from app.models import Usuario, UsuarioPrefixo
        from app.services.contexto_operacional import ContextoOperacionalService
        from app.services.exceptions import ContextoOperacionalError
        users = self.session.scalars(select(Usuario).join(UsuarioPrefixo).where(
            UsuarioPrefixo.id_prefixo == prefix_id, UsuarioPrefixo.ativo.is_(True)).with_for_update()).all()
        for user in users:
            remaining = [p for p in ContextoOperacionalService(self.session).ativos(user.id_usuario)
                         if p.id_prefixo != prefix_id]
            if user.situacao == "ativo" and not remaining:
                raise ContextoOperacionalError("Não é permitido desativar o último prefixo ativo de um usuário operacional")
            link = self.session.get(UsuarioPrefixo, (user.id_usuario, prefix_id))
            link.principal = False
            link.ativo = False
            if user.id_prefixo == prefix_id:
                user.id_prefixo = remaining[0].id_prefixo if remaining else None
