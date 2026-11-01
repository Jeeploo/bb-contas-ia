"""Adapter de manutenção para reutilizar o seed sem HTTP, servidor ou bypass público.

Só o comando CLI explícito usa este adapter. Os services mantêm as validações
cadastrais existentes. Cada escrita conserva a transação/idempotência do seed.
"""
import importlib
from urllib.parse import urlsplit
import httpx
from sqlalchemy import select
from app.schemas.vinculos import UsuarioPrefixosDefinicao, UnidadeConsumidoraCreate
from app.schemas.leitura_documental import ContextoDocumental, LeituraDocumental
from app.services.contexto_operacional import ContextoOperacionalService
from app.services.interpretacao_documental import InterpretacaoDocumentalService

RESOURCES = {
    'localidades': ('localidade','Localidade'), 'prefixos': ('prefixo','Prefixo'),
    'concessionarias': ('concessionaria','Concessionaria'), 'usuarios': ('usuario','Usuario'),
    'alcadas': ('alcada','Alcada'), 'contas_consumo': ('conta_consumo','ContaConsumo'),
    'regras_calculo': ('regra_calculo','RegraCalculo'), 'perfis_processamento': ('perfil_processamento','PerfilProcessamento'),
    'itens_regra': ('item_regra','ItemRegra'), 'sistemas_pagamento': ('sistema_pagamento','SistemaPagamento'),
    'calculos': ('calculo','Calculo'), 'ordens_pagamento': ('ordem_pagamento','OrdemPagamento'),
    'itens_pagamento': ('item_pagamento','ItemPagamento'), 'documentos': ('documento','Documento'),
    'extracoes_inteligentes': ('extracao_inteligente','ExtracaoInteligente'),
}


class MaintenanceSeedClient:
    def __init__(self, session):
        self.session = session

    def get(self, url, params=None):
        return self.request('GET',url,params=params or {})

    def post(self, url, json):
        return self.request('POST',url,data=json)

    def put(self, url, json):
        return self.request('PUT',url,data=json)

    def request(self, method, url, params=None, data=None):
        from app.models import UsuarioPrefixo, UnidadeConsumidora
        parts=urlsplit(url).path.removeprefix('/api/v1/').split('/')
        resource=parts[0]
        if resource=='usuarios' and len(parts)==3 and parts[2]=='prefixos':
            user=int(parts[1])
            if method=='GET':
                rows=self.session.scalars(select(UsuarioPrefixo).where(UsuarioPrefixo.id_usuario==user)).all()
                payload={'vinculos':[dict(id_prefixo=r.id_prefixo,ativo=r.ativo,principal=r.principal) for r in rows]}
            elif method=='PUT':
                entries=UsuarioPrefixosDefinicao.model_validate(data)
                ContextoOperacionalService(self.session).definir(user,entries.vinculos)
                payload=entries.model_dump(mode='json')
            else:
                raise RuntimeError('Operação de seed não suportada')
        elif resource=='documentos' and len(parts)==3 and parts[2]=='interpretacao' and method=='POST':
            extraction=InterpretacaoDocumentalService(self.session).registrar(int(parts[1]),
                LeituraDocumental.model_validate(data['leitura']),ContextoDocumental.model_validate(data['contexto']))
            from app.schemas.extracao_inteligente import ExtracaoInteligenteRead
            payload=ExtracaoInteligenteRead.model_validate(extraction).model_dump(mode='json')
        elif resource=='unidades_consumidoras':
            from app.schemas.vinculos import UnidadeConsumidoraRead
            if method=='GET':
                rows=self.session.scalars(select(UnidadeConsumidora).order_by(UnidadeConsumidora.id_unidade_consumidora)).all()
                payload=[UnidadeConsumidoraRead.model_validate(r).model_dump(mode='json') for r in rows]
            elif method=='POST':
                row=ContextoOperacionalService(self.session).cadastrar_unidade(UnidadeConsumidoraCreate.model_validate(data))
                payload=UnidadeConsumidoraRead.model_validate(row).model_dump(mode='json')
            else:
                raise RuntimeError('Operação de seed não suportada')
        else:
            module, name=RESOURCES[resource]
            service=getattr(importlib.import_module('app.services.'+module), name+'Service')(self.session)
            schema_module=importlib.import_module('app.schemas.'+module)
            read=getattr(schema_module,name+'Read')
            if method=='GET':
                rows=service.list(offset=(params or {}).get('offset',0),limit=(params or {}).get('limit',100))
                payload=[read.model_validate(r).model_dump(mode='json') for r in rows]
            elif method=='POST':
                create=getattr(schema_module,name+'Create').model_validate(data)
                payload=read.model_validate(service.create(create)).model_dump(mode='json')
            else:
                raise RuntimeError('Operação de seed não suportada')
        return httpx.Response(201 if method=='POST' else 200,json=payload,
            request=httpx.Request(method,'https://maintenance.invalid'+urlsplit(url).path))
