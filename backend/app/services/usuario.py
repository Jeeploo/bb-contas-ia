from app.models.usuario import Usuario
from app.repositories.usuario import UsuarioRepository
from app.repositories.alcada import AlcadaRepository
from app.repositories.prefixo import PrefixoRepository
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.services.base import BaseService
from app.services.exceptions import EntityNotFoundError


class UsuarioService(BaseService[Usuario, UsuarioCreate, UsuarioUpdate]):
    repository_class = UsuarioRepository
    foreign_keys = {
        "id_alcada": AlcadaRepository,
        "id_prefixo": PrefixoRepository,
    }

    def _validate_foreign_keys(self, data: UsuarioCreate | UsuarioUpdate) -> None:
        """FKs opcionais podem ser omitidas ou removidas explicitamente."""
        values = data.model_dump(exclude_unset=True)
        for field, repository_class in self.foreign_keys.items():
            entity_id = values.get(field)
            if entity_id is not None:
                if repository_class(self.session).get_by_id(entity_id) is None:
                    raise EntityNotFoundError(repository_class.model.__name__, entity_id)

    def create(self, data):
        from app.models.usuario_prefixo import UsuarioPrefixo
        from app.models.prefixo import Prefixo
        from app.services.exceptions import ContextoOperacionalError
        try:
            self._validate_foreign_keys(data)
            if data.situacao == "ativo":
                prefix = self.session.get(Prefixo, data.id_prefixo) if data.id_prefixo else None
                if prefix is None or prefix.situacao != "ativo":
                    raise ContextoOperacionalError("Usuário operacional precisa de ao menos um prefixo ativo")
            user = self.repository.create(data)
            if data.id_prefixo is not None:
                self.session.add(UsuarioPrefixo(id_usuario=user.id_usuario, id_prefixo=data.id_prefixo,
                                               ativo=True, principal=True))
                self.session.flush()
            self.session.commit()
            return user
        except Exception:
            self.session.rollback()
            raise

    def update(self, entity_id, data):
        from sqlalchemy import select
        from app.models.usuario_prefixo import UsuarioPrefixo
        from app.services.contexto_operacional import ContextoOperacionalService
        from app.services.exceptions import ContextoOperacionalError
        from app.schemas.vinculos import UsuarioPrefixoEntrada
        try:
            user = ContextoOperacionalService(self.session).usuario(entity_id, lock=True)
            self._validate_foreign_keys(data)
            user = self.repository.update(entity_id, data)
            if "id_prefixo" in data.model_fields_set and data.id_prefixo is not None:
                links = self.session.scalars(select(UsuarioPrefixo).where(UsuarioPrefixo.id_usuario == entity_id)).all()
                entries = [UsuarioPrefixoEntrada(id_prefixo=l.id_prefixo, ativo=l.ativo, principal=False)
                           for l in links if l.id_prefixo != data.id_prefixo]
                entries.append(UsuarioPrefixoEntrada(id_prefixo=data.id_prefixo, ativo=True, principal=True))
                ContextoOperacionalService(self.session).definir(entity_id, entries, commit=False)
            if user.situacao == "ativo" and not ContextoOperacionalService(self.session).ativos(entity_id):
                raise ContextoOperacionalError("Usuário operacional precisa de ao menos um prefixo ativo")
            from app.services.validacao_documental import revalidar_contextos
            revalidar_contextos(self.session)
            self.session.commit()
            return user
        except Exception:
            self.session.rollback()
            raise

    def delete(self, entity_id):
        from sqlalchemy import delete
        from app.models.usuario_prefixo import UsuarioPrefixo
        try:
            self.get_by_id(entity_id)
            self.session.execute(delete(UsuarioPrefixo).where(UsuarioPrefixo.id_usuario == entity_id))
            self.repository.delete(entity_id)
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            raise
