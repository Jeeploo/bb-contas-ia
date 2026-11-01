from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.db_dependency import get_db
from app.api.auth_dependencies import get_current_user, get_demo_session
from app.schemas.leitura_documental import ContextoDocumental
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.exceptions import ContextoOperacionalError, EntityNotFoundError


def get_contexto_operacional(id_prefixo: int | None = None, user=Depends(get_current_user),
        auth=Depends(get_demo_session), session: Session = Depends(get_db)):
    try:
        prefix = ContextoOperacionalService(session).resolver(user.id_usuario,
            id_prefixo if id_prefixo is not None else auth.id_prefixo)
    except (ContextoOperacionalError, EntityNotFoundError) as exc:
        raise HTTPException(403, str(exc)) from None
    return ContextoDocumental(id_usuario=user.id_usuario, id_prefixo=prefix.id_prefixo)
