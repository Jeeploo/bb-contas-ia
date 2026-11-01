from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.api.auth_dependencies import get_current_user, get_demo_session, check_origin
from app.core.config import settings
from app.services.auth_demo import authenticate, session_view, COOKIE
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.exceptions import ContextoOperacionalError, EntityNotFoundError

router = APIRouter(prefix='/auth', tags=['Autenticação DEMO'])


class LoginDemo(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    matricula: str = Field(min_length=1, max_length=100)
    senha: SecretStr = Field(min_length=1, max_length=256)
    segundo_fator: SecretStr = Field(min_length=1, max_length=100)


class PrefixoAtivo(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id_prefixo: int = Field(gt=0)


@router.post('/login')
def login(data: LoginDemo, request: Request, response: Response, session: Session = Depends(get_db)):
    if not settings.demo_auth_enabled:
        raise HTTPException(503, 'Autenticação DEMO não habilitada neste ambiente.')
    check_origin(request)
    from app.models.auth_demo import SessaoDemo
    from app.services.auth_demo import token_hash
    limiter = request.app.state.login_limiter
    ip = request.client.host if request.client else 'unknown'
    matricula = data.matricula.strip()
    retry = limiter.retry_after(ip, matricula, settings.login_window_seconds)
    if retry:
        raise HTTPException(429, 'Não foi possível entrar. Aguarde e tente novamente.', headers={'Retry-After': str(retry)})
    try:
        token, auth, user = authenticate(session, matricula, data.senha.get_secret_value(), data.segundo_fator.get_secret_value())
    except HTTPException as exc:
        if exc.status_code == 401:
            limiter.failure(ip, matricula, settings.login_max_attempts, settings.login_window_seconds, settings.login_block_seconds)
        raise
    # Rotação: novo login revoga o cookie anterior deste navegador.
    previous = session.get(SessaoDemo, token_hash(request.cookies.get(COOKIE, '')))
    if previous:
        session.delete(previous)
        session.commit()
    response.set_cookie(COOKIE, token, max_age=settings.session_ttl, httponly=True,
        secure=settings.demo_cookie_secure, samesite=settings.session_cookie_samesite, path='/api/v1')
    response.headers['Cache-Control'] = 'no-store'
    return session_view(session, auth, user)


@router.get('/sessao')
def current(response: Response, user=Depends(get_current_user), auth=Depends(get_demo_session), session: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    return session_view(session, auth, user)


@router.patch('/prefixo')
def select_prefix(data: PrefixoAtivo, response: Response, user=Depends(get_current_user), auth=Depends(get_demo_session), session: Session = Depends(get_db)):
    try:
        prefix = ContextoOperacionalService(session).resolver(user.id_usuario, data.id_prefixo)
    except (ContextoOperacionalError, EntityNotFoundError):
        raise HTTPException(403, 'Prefixo não autorizado.') from None
    auth.id_prefixo = prefix.id_prefixo
    session.commit()
    response.headers['Cache-Control'] = 'no-store'
    return session_view(session, auth, user)


@router.post('/logout', status_code=204)
def logout(response: Response, auth=Depends(get_demo_session), session: Session = Depends(get_db)):
    session.delete(auth)
    session.commit()
    response.delete_cookie(COOKIE, path='/api/v1', httponly=True,
        secure=settings.demo_cookie_secure, samesite=settings.session_cookie_samesite)
    response.headers['Cache-Control'] = 'no-store'
