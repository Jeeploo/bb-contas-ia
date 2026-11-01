"""Gemini nativo: bytes multimodais e contrato documental compartilhado."""
from datetime import datetime, timezone
import json
from time import perf_counter
import httpx
from google import genai
from google.genai import errors, types
from app.core.config import settings
from app.document_ai.base import DocumentAIError, InterpretacaoAI
from app.document_ai.normalizacao import normalizar_leitura
from app.document_ai.openai_provider import schema_leitura
from app.document_ai.prompt import INSTRUCOES, PROMPT_VERSION
from app.processing.arquivo_documental import validar_arquivo
from app.schemas.leitura_documental import LeituraDocumental
from app.services.exceptions import DocumentError


class GeminiDocumentAIProvider:
    provider = 'gemini'

    def __init__(self, client=None, modelo=None):
        self.client = client
        self.modelo = modelo if modelo is not None else settings.gemini_document_model

    def interpretar_documento(self, data, mime_type):
        started = perf_counter()
        meta = dict(provider=self.provider, modelo_solicitado=self.modelo,
                    data=datetime.now(timezone.utc).isoformat(), prompt_version=PROMPT_VERSION,
                    status='erro', tokens_entrada=None, tokens_saida=None, tokens_total=None)
        try:
            validar_arquivo(data, mime_type, verificar_pdf=True)
            if (not self.modelo or settings.gemini_document_timeout <= 0
                    or settings.gemini_document_max_output_tokens <= 0
                    or (self.client is None and not settings.gemini_api_key)):
                raise DocumentAIError('configuracao_ausente', 503)
            config = types.GenerateContentConfig(
                system_instruction=INSTRUCOES, response_mime_type='application/json',
                response_json_schema=schema_leitura(),
                max_output_tokens=settings.gemini_document_max_output_tokens)
            contents = [types.Part.from_bytes(data=data, mime_type=mime_type)]
            if self.client is not None:
                response = self.client.models.generate_content(model=self.modelo, contents=contents, config=config)
            else:
                # Context manager fecha conexões; uma tentativa, timeout em milissegundos.
                with genai.Client(api_key=settings.gemini_api_key, vertexai=False,
                        http_options=types.HttpOptions(
                            timeout=int(settings.gemini_document_timeout * 1000),
                            retry_options=types.HttpRetryOptions(attempts=1))) as client:
                    response = client.models.generate_content(model=self.modelo, contents=contents, config=config)
            usage = response.usage_metadata
            meta.update(modelo=response.model_version or self.modelo, response_id=response.response_id,
                        tokens_entrada=usage.prompt_token_count if usage else None,
                        tokens_saida=usage.candidates_token_count if usage else None,
                        tokens_total=usage.total_token_count if usage else None)
            if not response.candidates or any(c.finish_reason != types.FinishReason.STOP for c in response.candidates):
                raise DocumentAIError('resposta_incompleta')
            original = json.loads(response.text)
            if not isinstance(original, dict) or set(original) != set(LeituraDocumental.model_fields):
                raise DocumentAIError('resposta_invalida')
            if not any(value is not None and value != '' for value in original.values()):
                raise DocumentAIError('resposta_vazia')
            leitura = normalizar_leitura(original)
            meta.update(status='concluida', latencia_ms=round((perf_counter()-started)*1000))
            return InterpretacaoAI(leitura, original, meta)
        except DocumentAIError as exc:
            error = exc
        except DocumentError:
            error = DocumentAIError('arquivo_invalido', 422)
        except (httpx.TimeoutException, TimeoutError):
            error = DocumentAIError('timeout', 504)
        except httpx.TransportError:
            error = DocumentAIError('provider_indisponivel', 503)
        except errors.APIError as exc:
            # Não logar mensagem, corpo, request ou headers do SDK.
            code, status = {
                400: ('requisicao_provider_invalida', 422),
                401: ('autenticacao_provider', 503), 403: ('autenticacao_provider', 503),
                404: ('modelo_indisponivel', 503), 429: ('rate_limit', 429),
                408: ('timeout', 504), 504: ('timeout', 504),
            }.get(exc.code, ('provider_indisponivel', 503) if exc.code and exc.code >= 500 else ('erro_provider', 502))
            # Distinguir schema inválido sem persistir texto do fornecedor.
            if exc.code == 400 and any(key in (exc.message or '').lower() for key in ('response_json_schema', 'response_schema')):
                code = 'schema_invalido'
            error = DocumentAIError(code, status)
        except (ValueError, TypeError, AttributeError):
            error = DocumentAIError('resposta_invalida')
        meta.update(erro_tecnico=error.codigo, latencia_ms=round((perf_counter()-started)*1000))
        error.metadados = meta
        raise error from None
