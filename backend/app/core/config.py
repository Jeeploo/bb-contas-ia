"""Configuração única: defaults locais, validação estrita para ambiente externo."""
import os
from urllib.parse import urlsplit
from dotenv import load_dotenv

load_dotenv()


def boolean(env, name, default=False, legacy=None):
    value = env.get(name, env.get(legacy, str(default)) if legacy else str(default)).strip().lower()
    if value not in {'true', 'false'}:
        raise ValueError(f'{name} deve ser true ou false')
    return value == 'true'


def positive(env, name, default, maximum=None):
    try:
        value = int(env.get(name, default))
    except (ValueError, TypeError):
        raise ValueError(f'{name} deve ser inteiro positivo') from None
    if value <= 0 or maximum and value > maximum:
        raise ValueError(f'{name} fora do intervalo permitido')
    return value


def database_url(value):
    for prefix in ('postgres://', 'postgresql://'):
        if value.startswith(prefix):
            return 'postgresql+psycopg://' + value[len(prefix):]
    return value


class Settings:
    def __init__(self, env=None):
        env = os.environ if env is None else env
        self.app_env = env.get('APP_ENV', 'development').strip().lower()
        if self.app_env not in {'development', 'test', 'homologation', 'staging', 'production'}:
            raise ValueError('APP_ENV inválido')
        self.external = self.app_env not in {'development', 'test'}
        # Compatibilidade dos ambientes locais anteriores; exemplos usam apenas os nomes canônicos.
        self.demo_auth_enabled = boolean(env, 'DEMO_MODE', legacy='DEMO_AUTH_ENABLED')
        self.demo_cookie_secure = boolean(env, 'SESSION_COOKIE_SECURE', self.external, 'DEMO_COOKIE_SECURE')
        self.session_cookie_samesite = env.get('SESSION_COOKIE_SAMESITE', 'strict').strip().lower()
        self.session_ttl = positive(env, 'SESSION_TTL', 28800)
        self.login_max_attempts = positive(env, 'LOGIN_MAX_ATTEMPTS', 5)
        self.login_block_seconds = positive(env, 'LOGIN_BLOCK_SECONDS', 300)
        self.login_window_seconds = positive(env, 'LOGIN_WINDOW_SECONDS', 300)
        self.frontend_origin = env.get('FRONTEND_ORIGIN', '').strip()
        self.port = positive(env, 'PORT', 8000, 65535)
        self.forwarded_allow_ips = env.get('FORWARDED_ALLOW_IPS', '127.0.0.1')
        self.document_ai_provider = env.get('DOCUMENT_AI_PROVIDER', 'openai').strip().lower()
        self.gemini_api_key = env.get('GEMINI_API_KEY', '')
        self.gemini_document_model = env.get('GEMINI_DOCUMENT_MODEL', 'gemini-2.5-flash-lite').strip()
        self.gemini_document_timeout = float(env.get('GEMINI_DOCUMENT_TIMEOUT', '90'))
        self.gemini_document_max_output_tokens = positive(env, 'GEMINI_DOCUMENT_MAX_OUTPUT_TOKENS', 6000)
        self.uf_mvp = env.get('UF_MVP', 'PE').strip().upper()
        self.openai_api_key = env.get('OPENAI_API_KEY', '')
        self.openai_document_model = env.get('OPENAI_DOCUMENT_MODEL', '').strip()
        self.openai_document_timeout = float(env.get('OPENAI_DOCUMENT_TIMEOUT', '90'))
        self.openai_document_max_output_tokens = positive(env, 'OPENAI_DOCUMENT_MAX_OUTPUT_TOKENS', 6000)
        self.app_name = 'BB Contas IA'
        self.document_storage_backend = env.get('DOCUMENT_STORAGE_BACKEND', 'filesystem')  # compatibilidade local
        self.document_storage_provider = env.get('DOCUMENT_STORAGE_PROVIDER', 'local').strip().lower()
        self.r2_endpoint = env.get('R2_ENDPOINT', '').strip()
        self.r2_bucket = env.get('R2_BUCKET', '').strip()
        self.r2_access_key_id = env.get('R2_ACCESS_KEY_ID', '')
        self.r2_secret_access_key = env.get('R2_SECRET_ACCESS_KEY', '')
        self.r2_region = env.get('R2_REGION', 'auto').strip()
        self.document_storage_path = env.get('DOCUMENT_STORAGE_PATH', './storage/documentos')
        self.document_storage_persistent = boolean(env, 'DOCUMENT_STORAGE_PERSISTENT')
        self.document_max_size_bytes = positive(env, 'DOCUMENT_MAX_SIZE_BYTES', 10485760)
        self.max_ocr_pages = positive(env, 'MAX_OCR_PAGES', 10)
        self.database_url = database_url(env.get('DATABASE_URL', ''))
        self.validate()

    @property
    def allowed_origins(self):
        if self.external:
            return [self.frontend_origin]
        return list(dict.fromkeys(['http://127.0.0.1:5173', 'http://localhost:5173'] +
                                 ([self.frontend_origin] if self.frontend_origin else [])))

    def validate(self):
        if self.session_cookie_samesite not in {'strict', 'lax', 'none'}:
            raise ValueError('SESSION_COOKIE_SAMESITE deve ser strict, lax ou none')
        if self.session_cookie_samesite == 'none' and not self.demo_cookie_secure:
            raise ValueError('SameSite=None exige SESSION_COOKIE_SECURE=true')
        if self.frontend_origin:
            parsed = urlsplit(self.frontend_origin)
            if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username
                    or parsed.password or parsed.path or parsed.query or parsed.fragment
                    or '*' in self.frontend_origin):
                raise ValueError('FRONTEND_ORIGIN deve ser uma origem exata, sem caminho ou wildcard')
        if self.document_storage_backend != 'filesystem':
            raise ValueError('DOCUMENT_STORAGE_BACKEND não implementado; use filesystem com volume persistente')
        if self.document_storage_provider not in {'local', 'r2'}:
            raise ValueError('DOCUMENT_STORAGE_PROVIDER deve ser local ou r2')
        if self.document_storage_provider == 'r2':
            self.validate_r2()
        if self.external:
            if not self.frontend_origin.startswith('https://'):
                raise ValueError('Ambiente externo exige FRONTEND_ORIGIN HTTPS')
            if not self.demo_cookie_secure:
                raise ValueError('Ambiente externo exige SESSION_COOKIE_SECURE=true')
            from sqlalchemy.engine import make_url
            try:
                db = make_url(self.database_url)
                valid = db.drivername == 'postgresql+psycopg' and db.host and db.host not in {'localhost', '127.0.0.1', '::1'}
            except Exception:
                valid = False
            if not valid:
                raise ValueError('Ambiente externo exige DATABASE_URL PostgreSQL externo válida')
            from pathlib import Path
            if self.document_storage_provider == 'local' and (not self.document_storage_persistent or not Path(self.document_storage_path).is_absolute()):
                raise ValueError('Ambiente externo exige volume persistente e DOCUMENT_STORAGE_PATH absoluto')


    def validate_r2(self):
        endpoint = urlsplit(self.r2_endpoint)
        if (endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password
                or endpoint.path not in {'', '/'} or endpoint.query or endpoint.fragment):
            raise ValueError('R2_ENDPOINT deve ser uma origem HTTPS válida, sem credenciais ou caminho')
        if not self.r2_bucket or '/' in self.r2_bucket or not self.r2_access_key_id or not self.r2_secret_access_key or not self.r2_region:
            raise ValueError('Configuração R2 incompleta: informe bucket, credenciais e região')


settings = Settings()
