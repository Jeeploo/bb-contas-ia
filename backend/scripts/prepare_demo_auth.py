"""Configura acesso local dos usuários já criados pelo seed, sem duplicá-los.

.venv/bin/python scripts/prepare_demo_auth.py --ambiente-demo --arquivo /tmp/bb-demo-acessos.json
O arquivo privado é criado uma vez. Reexecutar preserva hashes e credenciais.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
from sqlalchemy import select, delete
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import SessionLocal
from app.models import Usuario, Prefixo, UsuarioPrefixo
from app.models.auth_demo import CredencialDemo, SessaoDemo
from app.services.auth_demo import hash_secret, verify_secret
from app.services.contexto_operacional import ContextoOperacionalService
from app.schemas.vinculos import UsuarioPrefixoEntrada

PROFILES = [
    ('DEMO-maker', 'Maker Recife', ['REC-DEMO']),
    ('DEMO-maker-paulista', 'Maker Paulista', ['PAU-DEMO']),
    ('DEMO-maker-multi', 'Maker Multi-Prefixo', ['REC-DEMO','PAU-DEMO']),
    ('DEMO-checker', 'Checker', ['REC-DEMO','PAU-DEMO']),
    ('DEMO-limite-baixo', 'Usuário de alçada reduzida', ['REC-DEMO']),
]


def provision(session, access):
    """Reutiliza identidades/alçadas. Escopo explícito e controlado do seed DEMO."""
    for matricula, label, codes in PROFILES:
        user = session.scalar(select(Usuario).where(Usuario.matricula == matricula))
        if user is None or user.situacao != 'ativo':
            raise RuntimeError(f'Usuário DEMO ausente/inativo: {matricula}. Prepare o seed antes.')
        prefixes = [session.scalar(select(Prefixo).where(Prefixo.codigo_prefixo == code, Prefixo.situacao == 'ativo')) for code in codes]
        if any(p is None for p in prefixes):
            raise RuntimeError('Prefixos DEMO ausentes. Prepare o seed antes.')
        ids = [p.id_prefixo for p in prefixes]
        links = list(session.scalars(select(UsuarioPrefixo).where(UsuarioPrefixo.id_usuario == user.id_usuario)))
        desired = [UsuarioPrefixoEntrada(id_prefixo=pid,ativo=True,principal=i==0) for i,pid in enumerate(ids)]
        if {(l.id_prefixo,l.ativo,l.principal) for l in links if l.ativo} != {(pid,True,i==0) for i,pid in enumerate(ids)}:
            ContextoOperacionalService(session).definir(user.id_usuario, desired, commit=False)
        credential = session.get(CredencialDemo, user.id_usuario)
        if credential is not None:
            values = access[matricula]
            if not (verify_secret(values['senha'], credential.senha_hash) and verify_secret(values['segundo_fator'], credential.fator_hash)):
                raise RuntimeError('Arquivo de acesso não corresponde às credenciais existentes. Use o arquivo original; nenhuma senha foi alterada.')
        if credential is None:
            values = access[matricula]
            session.add(CredencialDemo(id_usuario=user.id_usuario,
                senha_hash=hash_secret(values['senha']), fator_hash=hash_secret(values['segundo_fator'])))
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
    if args.arquivo.exists():
        if args.arquivo.stat().st_mode & 0o077:
            parser.error('Arquivo de credenciais deve ter permissão 0600.')
        access=json.loads(args.arquivo.read_text())
    else:
        access={m:dict(perfil=label,senha=secrets.token_urlsafe(16),segundo_fator=f'{secrets.randbelow(1000000):06d}') for m,label,_ in PROFILES}
        fd=os.open(args.arquivo,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as target:
            json.dump(access,target,indent=2,ensure_ascii=False)
    with SessionLocal() as session:
        provision(session,access)
    print('Acesso DEMO configurado para os cinco usuários existentes. Credenciais no arquivo privado informado.')


if __name__=='__main__':
    main()
