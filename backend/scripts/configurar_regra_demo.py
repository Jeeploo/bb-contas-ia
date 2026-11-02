"""Uso: python -m scripts.configurar_regra_demo --documento ID.

Configura somente o prefixo e a competência do documento informado, sem IA.
"""
import argparse
from sqlalchemy.orm import Session
from app.core.database import engine
from app.services.regra_demo import configurar_regra_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--documento', type=int, required=True)
    args = parser.parse_args()
    with Session(engine) as session, session.begin():
        profile = configurar_regra_demo(session, args.documento)
        print(f'Regra DEMO configurada: prefixo={profile.id_prefixo}, perfil={profile.id_perfil}, regra={profile.id_regra}')


if __name__ == '__main__':
    main()
