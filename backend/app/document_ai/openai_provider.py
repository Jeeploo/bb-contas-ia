import base64
from datetime import datetime, timezone
import json
import logging
import re
from decimal import Decimal
from typing import get_args
from time import perf_counter
import openai
from app.core.config import settings
from app.schemas.leitura_documental import LeituraDocumental
from app.document_ai.base import InterpretacaoAI, DocumentAIError
from app.document_ai.normalizacao import normalizar_leitura
from app.document_ai.prompt import INSTRUCOES, PROMPT_VERSION
from app.processing.arquivo_documental import validar_arquivo


logger = logging.getLogger(__name__)


def _diagnostico_openai(exc, encoded):
    """Diagnóstico temporário: allowlist, sem serializar exceção/request/headers."""
    body = exc.body if isinstance(exc.body, dict) else {}
    body = body.get('error', body)
    body = body if isinstance(body, dict) else {}

    def sanitizar(value, limite):
        if not isinstance(value, str):
            return None
        for segredo in (settings.openai_api_key, encoded):
            if segredo:
                value = value.replace(segredo, '[REDACTED]')
        # Suprime valores citados (inclusive conteúdo ecoado), credenciais,
        # data URLs, identificadores numéricos e blocos longos/base64.
        value = re.sub(r"data:[^\s]+|Bearer\s+\S+|sk-[\w-]+", '[REDACTED]', value, flags=re.I)
        value = re.sub(r"\"[^\"]*\"|'[^']*'|`[^`]*`", '[REDACTED]', value, flags=re.S)
        value = re.sub(r'[A-Za-z0-9+/=_-]{40,}|\d{5,}', '[REDACTED]', value)
        return ' '.join(value.split())[:limite]

    logger.warning('%s', json.dumps({
        'status_http': getattr(exc, 'status_code', None),
        'error.code': sanitizar(body.get('code'), 100),
        'error.type': sanitizar(body.get('type'), 100),
        'mensagem': sanitizar(body.get('message'), 500),
        'request_id': sanitizar(getattr(exc, 'request_id', None), 150),
    }, ensure_ascii=False))


def schema_leitura():
    """Adapta o JSON Schema canônico para o subconjunto estrito da API, sem DTO paralelo."""
    schema = LeituraDocumental.model_json_schema(mode='validation')
    for name, field in LeituraDocumental.model_fields.items():
        if Decimal in get_args(field.annotation):
            # O ramo numérico mantém minimum/maximum sem a regex de strings
            # Decimal. Precisão e escala continuam validadas pelo Pydantic.
            prop = schema['properties'][name]
            prop['anyOf'] = [branch for branch in prop['anyOf']
                             if branch.get('type') != 'string']
    def strict(node):
        if isinstance(node, dict):
            node.pop('default', None)
            if node.get('type') == 'object':
                node['required'] = list(node.get('properties', {}))
                node['additionalProperties'] = False
            for value in node.values():
                strict(value)
        elif isinstance(node, list):
            for value in node:
                strict(value)
    strict(schema)
    schema['properties']['tipo_documento'] = {'anyOf': [
        {'type':'string', 'enum':['CONTA_ENERGIA','CONTA_AGUA','OUTRO']}, {'type':'null'}]}
    return schema


class OpenAIDocumentAIProvider:
    provider = 'openai'

    def __init__(self, client=None, modelo=None):
        self.modelo = modelo if modelo is not None else settings.openai_document_model
        self.client = client

    def interpretar_documento(self, data, mime_type):
        validar_arquivo(data, mime_type, verificar_pdf=True)
        meta = dict(provider=self.provider, modelo_solicitado=self.modelo,
                    data=datetime.now(timezone.utc).isoformat(), prompt_version=PROMPT_VERSION,
                    status='erro', tokens_entrada=None, tokens_saida=None)
        encoded = None
        started = perf_counter()
        try:
            if (not self.modelo or settings.openai_document_timeout <= 0
                    or settings.openai_document_max_output_tokens <= 0
                    or (self.client is None and not settings.openai_api_key)):
                raise DocumentAIError('configuracao_ausente', 503)
            # Sem retries ocultos nem armazenamento de Responses. Credencial nunca é logada.
            client = self.client or openai.OpenAI(api_key=settings.openai_api_key,
                timeout=settings.openai_document_timeout, max_retries=0)
            encoded = base64.b64encode(data).decode('ascii')
            if mime_type == 'application/pdf':
                content = dict(type='input_file', filename='documento.pdf',
                               file_data='data:application/pdf;base64,'+encoded)
            else:
                content = dict(type='input_image', image_url=f'data:{mime_type};base64,{encoded}', detail='high')
            response = client.responses.create(model=self.modelo, store=False,
                instructions=INSTRUCOES, input=[{'role':'user','content':[content]}],
                max_output_tokens=settings.openai_document_max_output_tokens,
                text={'format':dict(type='json_schema', name='leitura_documental', strict=True, schema=schema_leitura())})
            meta.update(modelo=response.model, response_id=response.id,
                        tokens_entrada=response.usage.input_tokens if response.usage else None,
                        tokens_saida=response.usage.output_tokens if response.usage else None)
            if not isinstance(response.output, list):
                raise DocumentAIError('resposta_invalida')
            if response.status != 'completed':
                raise DocumentAIError('resposta_incompleta')
            if any(getattr(part, 'type', None) == 'refusal'
                   for item in response.output for part in (getattr(item, 'content', []) or [])):
                raise DocumentAIError('recusa_modelo')
            if not response.output_text or not response.output_text.strip():
                raise DocumentAIError('resposta_vazia')
            try:
                original = json.loads(response.output_text)
            except (ValueError, TypeError):
                raise DocumentAIError('resposta_invalida') from None
            if not isinstance(original, dict) or set(original) != set(LeituraDocumental.model_fields):
                raise DocumentAIError('resposta_invalida')
            if not any(value is not None and value != '' for value in original.values()):
                raise DocumentAIError('resposta_vazia')
            leitura = normalizar_leitura(original)
            meta.update(status='concluida', latencia_ms=round((perf_counter()-started)*1000))
            return InterpretacaoAI(leitura, original, meta)
        except openai.APIError as exc:
            _diagnostico_openai(exc, encoded)
            if isinstance(exc, openai.APITimeoutError):
                error = DocumentAIError('timeout', 504)
            elif isinstance(exc, openai.RateLimitError):
                error = DocumentAIError('rate_limit', 429)
            elif isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
                error = DocumentAIError('autenticacao_provider', 503)
            elif isinstance(exc, openai.BadRequestError):
                error = DocumentAIError('requisicao_provider_invalida', 422)
            elif isinstance(exc, (openai.APIConnectionError, openai.InternalServerError)):
                error = DocumentAIError('provider_indisponivel', 503)
            else:
                error = DocumentAIError('erro_provider', 502)
        except DocumentAIError as exc:
            error = exc
        except (AttributeError, TypeError, ValueError):
            error = DocumentAIError('resposta_invalida')
        meta.update(status='erro', erro_tecnico=error.codigo, latencia_ms=round((perf_counter()-started)*1000))
        error.metadados = meta
        raise error from None
