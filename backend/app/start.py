"""Entrypoint portátil; não executa migrations, seed ou chamadas de IA."""
import os
import sys
from app.core.config import settings


def command():
    return [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0',
            '--port', str(settings.port), '--no-access-log', '--proxy-headers',
            '--forwarded-allow-ips', settings.forwarded_allow_ips]


def main():
    args = command()
    os.execv(args[0], args)


if __name__ == '__main__':
    main()
