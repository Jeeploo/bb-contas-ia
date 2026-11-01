"""Autenticação exclusivamente DEMO, sem identidade ou credenciais institucionais."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.models import Usuario, UsuarioPrefixo
from app.models.auth_demo import CredencialDemo, SessaoDemo
from app.services.contexto_operacional import ContextoOperacionalService

COOKIE = 'bb_demo_session'


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_secret(value):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode(), salt=salt, n=16384, r=8, p=1)
    return f'scrypt$16384$8$1${salt.hex()}${digest.hex()}'


def verify_secret(value, encoded):
    try:
        algorithm, n, r, p, salt, expected = encoded.split('$')
        if (algorithm, n, r, p) != ('scrypt', '16384', '8', '1'):
            return False
        actual = hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


DUMMY_HASH = hash_secret('credential-not-configured')


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(session, matricula, senha, fator):
    user = session.scalar(select(Usuario).where(Usuario.matricula == matricula))
    credential = session.get(CredencialDemo, user.id_usuario) if user else None
    password_ok = verify_secret(senha, credential.senha_hash if credential else DUMMY_HASH)
    factor_ok = verify_secret(fator, credential.fator_hash if credential else DUMMY_HASH)
    if not (user and user.situacao == 'ativo' and credential and password_ok and factor_ok):
        raise HTTPException(401, 'Matrícula, senha ou código DEMO inválidos.')
    prefixes = ContextoOperacionalService(session).ativos(user.id_usuario)
    if not prefixes:
        raise HTTPException(403, 'Usuário sem prefixo ativo autorizado.')
    principal = session.scalar(select(UsuarioPrefixo.id_prefixo).where(
        UsuarioPrefixo.id_usuario == user.id_usuario, UsuarioPrefixo.ativo.is_(True),
        UsuarioPrefixo.principal.is_(True)))
    prefix_ids = {p.id_prefixo for p in prefixes}
    selected = prefixes[0].id_prefixo if len(prefixes) == 1 else principal if principal in prefix_ids else None
    token = secrets.token_urlsafe(32)
    auth = SessaoDemo(token_hash=token_hash(token), id_usuario=user.id_usuario,
        id_prefixo=selected, expira_em=now() + timedelta(seconds=settings.session_ttl))
    session.add(auth)
    session.commit()
    return token, auth, user


def session_view(session, auth, user):
    prefixes = ContextoOperacionalService(session).ativos(user.id_usuario)
    ids = {p.id_prefixo for p in prefixes}
    selected = auth.id_prefixo if auth.id_prefixo in ids else None
    if len(prefixes) == 1:
        selected = prefixes[0].id_prefixo
    principal = session.scalar(select(UsuarioPrefixo.id_prefixo).where(
        UsuarioPrefixo.id_usuario == user.id_usuario, UsuarioPrefixo.ativo.is_(True),
        UsuarioPrefixo.principal.is_(True)))
    return dict(usuario=dict(id_usuario=user.id_usuario, matricula=user.matricula,
        nome=user.nome, funcao=user.funcao), prefixos=[dict(id_prefixo=p.id_prefixo,
        codigo_prefixo=p.codigo_prefixo, nome=p.nome) for p in prefixes],
        id_prefixo_principal=principal if principal in ids else None,
        id_prefixo_ativo=selected, expira_em=auth.expira_em)
