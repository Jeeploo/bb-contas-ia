"""Configura acesso local dos usuários já criados pelo seed, sem duplicá-los.

.venv/bin/python scripts/prepare_demo_auth.py --ambiente-demo --arquivo /tmp/bb-demo-acessos.json
Credenciais previsíveis 1/1 a 5/5, exclusivamente em DEMO_MODE=true.
Reexecutar preserva hashes já correspondentes.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from sqlalchemy import select, delete
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import SessionLocal
from app.models import Usuario
from app.models.auth_demo import CredencialDemo, SessaoDemo
from app.services.auth_demo import hash_secret, verify_secret

PROFILES = [
    ('DEMO-maker', 'Maker Recife', ['REC-DEMO']),
    ('DEMO-maker-paulista', 'Maker Paulista', ['PAU-DEMO']),
    ('DEMO-maker-multi', 'Maker Multi-Prefixo', ['REC-DEMO','PAU-DEMO']),
    ('DEMO-checker', 'Checker', ['REC-DEMO','PAU-DEMO']),
    ('DEMO-limite-baixo', 'Alçada reduzida', ['REC-DEMO']),
]


def demo_access():
    return {m: dict(perfil=label, senha=str(i), segundo_fator=str(i))
            for i, (m, label, _) in enumerate(PROFILES, 1)}


def provision(session, access=None):
    """Atualiza somente hashes; preserva usuários, vínculos e alçadas existentes."""
    from app.core.config import settings
    if not settings.demo_auth_enabled:
        raise RuntimeError('A preparação exige DEMO_MODE=true.')
    access = demo_access() if access is None else access
    for matricula, _, _ in PROFILES:
        user = session.scalar(select(Usuario).where(Usuario.matricula == matricula))
        if user is None or user.situacao != 'ativo':
            raise RuntimeError(f'Usuário DEMO ausente/inativo: {matricula}. Prepare o seed antes.')
        values = access[matricula]
        credential = session.get(CredencialDemo, user.id_usuario)
        if credential and verify_secret(values['senha'], credential.senha_hash) and verify_secret(values['segundo_fator'], credential.fator_hash):
            continue
        if credential is None:
            credential = CredencialDemo(id_usuario=user.id_usuario)
            session.add(credential)
        credential.senha_hash = hash_secret(values['senha'])
        credential.fator_hash = hash_secret(values['segundo_fator'])
        session.execute(delete(SessaoDemo).where(SessaoDemo.id_usuario == user.id_usuario))
    session.commit()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ambiente-demo',action='store_true',required=True)
    parser.add_argument('--arquivo',type=Path,required=True)
    args=parser.parse_args()
    from app.core.config import settings
    if not settings.demo_auth_enabled:
        parser.error('A preparação exige DEMO_MODE=true e --ambiente-demo')
    access = demo_access()
    fd = os.open(args.arquivo, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as target:
        os.fchmod(target.fileno(), 0o600)
        json.dump(access, target, indent=2, ensure_ascii=False)
    with SessionLocal() as session:
        provision(session,access)
    print('Acesso DEMO configurado para os cinco usuários existentes. Credenciais no arquivo privado informado.')


if __name__=='__main__':
    main()
