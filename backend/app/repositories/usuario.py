from app.models.usuario import Usuario
from app.repositories.base import BaseRepository
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate


class UsuarioRepository(BaseRepository[Usuario, UsuarioCreate, UsuarioUpdate]):
    model = Usuario
