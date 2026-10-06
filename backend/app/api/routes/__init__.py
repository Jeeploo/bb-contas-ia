from fastapi import APIRouter

from app.api.routes import (
    concessionaria,
    conta_consumo,
    dado_extraido,
    documento,
    extracao_inteligente,
    localidade,
    prefixo,
)


router = APIRouter(prefix="/api/v1")
router.include_router(localidade.router)
router.include_router(prefixo.router)
router.include_router(concessionaria.router)
router.include_router(conta_consumo.router)
router.include_router(documento.router)
router.include_router(extracao_inteligente.router)
router.include_router(dado_extraido.router)
