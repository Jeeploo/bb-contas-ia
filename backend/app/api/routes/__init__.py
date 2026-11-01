from fastapi import APIRouter

from app.api.routes import (
    perfil_processamento,
    item_extraido,
    alcada,
    usuario,
    sistema_pagamento,
    ordem_pagamento,
    item_pagamento,
    aprovacao,
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
router.include_router(alcada.router)
router.include_router(usuario.router)
router.include_router(sistema_pagamento.router)
router.include_router(ordem_pagamento.router)
router.include_router(item_pagamento.router)
router.include_router(aprovacao.router)

router.include_router(perfil_processamento.router)
router.include_router(item_extraido.router)

from app.api.routes.contexto_documental import router as contexto_router
router.include_router(contexto_router)
