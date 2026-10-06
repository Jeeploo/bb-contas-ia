from fastapi import APIRouter

from app.api.routes import concessionaria, localidade, prefixo


router = APIRouter(prefix="/api/v1")
router.include_router(localidade.router)
router.include_router(prefixo.router)
router.include_router(concessionaria.router)
