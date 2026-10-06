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
