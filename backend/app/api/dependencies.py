from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal


def get_db() -> Iterator[Session]:
    """Fornece uma sessão por requisição; transações pertencem aos services."""
    with SessionLocal() as session:
        yield session


def get_contexto_operacional(id_usuario: int | None = None, id_prefixo: int | None = None):
    """Identidade declarada para ambiente sem autenticação; substituir por principal autenticado.

    Ausência mantém apenas o fluxo legado de extração, sem aprovação documental.
    """
    from fastapi import HTTPException
    from app.schemas.leitura_documental import ContextoDocumental
    if id_usuario is None:
        if id_prefixo is not None:
            raise HTTPException(status_code=422, detail="Informe o usuário do contexto")
        return None
    if id_usuario <= 0 or (id_prefixo is not None and id_prefixo <= 0):
        raise HTTPException(status_code=422, detail="Identificadores devem ser positivos")
    return ContextoDocumental(id_usuario=id_usuario, id_prefixo=id_prefixo)
