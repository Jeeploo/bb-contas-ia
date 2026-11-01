import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from app.api.routes import router, public_router
from app.core.config import settings
from app.core.database import test_database_connection
from app.services.login_rate_limit import LoginRateLimiter

logger = logging.getLogger(__name__)


def root():
    return {'message': 'API BB Contas IA funcionando'}


def health():
    try:
        connected = test_database_connection() == 1
    except Exception:
        connected = False
        logger.warning('health_database_unavailable')
    payload = {'status': 'ok', 'database': 'connected' if connected else 'error'}
    return JSONResponse(payload, status_code=200 if connected else 503)


async def safe_validation_error(request, exc):
    if request.url.path.startswith('/api/v1/auth/'):
        return JSONResponse(status_code=422, content={'detail': [
            {key: error[key] for key in ('type', 'loc', 'msg')} for error in exc.errors()]})
    return await request_validation_exception_handler(request, exc)


def create_app():
    settings.validate()
    app = FastAPI(title=settings.app_name)
    app.state.login_limiter = LoginRateLimiter()
    app.include_router(public_router)
    app.include_router(router)
    app.add_api_route('/', root, methods=['GET'])
    app.add_api_route('/health', health, methods=['GET'])
    app.add_exception_handler(RequestValidationError, safe_validation_error)

    @app.middleware('http')
    async def safe_external_errors(request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            if not settings.external:
                raise
            # SQL/SDK exceptions can contain parameters or provider payloads.
            # No repr, stack locals, headers, body, raw URL or query string.
            logger.error('http_unhandled error_type=%s method=%s', type(exc).__name__, request.method)
            return JSONResponse({'detail': 'Falha interna ao concluir a operação.'}, status_code=500)
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
        allow_methods=['GET', 'POST', 'PATCH', 'PUT'], allow_headers=['Content-Type'],
        allow_credentials=True)
    return app


app = create_app()
