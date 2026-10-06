from fastapi import APIRouter

from app.api.routes import (
    calculo,
    concessionaria,
    conta_consumo,
    dado_extraido,
    documento,
    extracao_inteligente,
    item_regra,
    localidade,
    prefixo,
    regra_calculo,
)


router = APIRouter(prefix="/api/v1")
router.include_router(localidade.router)
router.include_router(prefixo.router)
router.include_router(concessionaria.router)
router.include_router(conta_consumo.router)
router.include_router(documento.router)
router.include_router(extracao_inteligente.router)
router.include_router(dado_extraido.router)
router.include_router(regra_calculo.router)
router.include_router(item_regra.router)
router.include_router(calculo.router)
