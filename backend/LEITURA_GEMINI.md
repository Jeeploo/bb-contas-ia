# Providers documentais: OpenAI e Gemini

`OpenAIDocumentAIProvider` permanece disponível e é o padrão. O resolver
`app.document_ai.factory.get_document_ai_provider()` seleciona um único provider por
`DOCUMENT_AI_PROVIDER=openai|gemini`. Valor desconhecido gera o código seguro
`document_ai_provider_desconhecido` (503). Não há fallback automático.

Configuração de desenvolvimento (no `.env` privado, nunca versionar chave):

```dotenv
DOCUMENT_AI_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_DOCUMENT_MODEL=gemini-2.5-flash-lite
GEMINI_DOCUMENT_TIMEOUT=90
GEMINI_DOCUMENT_MAX_OUTPUT_TOKENS=6000
```

O modelo pode ser trocado por ambiente. OpenAI mantém suas variáveis
`OPENAI_API_KEY`, `OPENAI_DOCUMENT_MODEL`, `OPENAI_DOCUMENT_TIMEOUT` e
`OPENAI_DOCUMENT_MAX_OUTPUT_TOKENS`. Instale `requirements.txt` no ambiente virtual;
o SDK oficial adicionado é `google-genai==2.34.0`.

## Contrato e transporte

Gemini usa `client.models.generate_content` com `response_mime_type=application/json`
e `response_json_schema` reutilizando `schema_leitura()` da integração OpenAI.
Nenhum DTO de domínio paralelo ou adapter adicional foi necessário. Todas as
propriedades são exigidas; dados ausentes são null. A saída passa por parsing JSON,
checagem de campos, normalização existente e validação Pydantic de `LeituraDocumental`.
Precisão monetária e consistência de consumo continuam verificadas localmente.

O prompt compartilhado trata o documento como dado não confiável e restringe a
classificação a CONTA_ENERGIA, CONTA_AGUA e OUTRO (null para ilegível/ambíguo).
UF, prefixo e contexto esperados não são enviados. Nenhuma decisão de negócio foi
transferida: normalização → persistência existente → `ValidacaoDocumentalService`.
Cálculo, autenticação, regras determinísticas e processamento legado permanecem iguais.

PDF é enviado diretamente por `types.Part.from_bytes(..., mime_type='application/pdf')`,
sem renderização ou OCR manual. JPG/JPEG/PNG usam o mesmo mecanismo multimodal com
MIME correspondente. Validação e limite local de tamanho continuam em vigor (10 MiB
por padrão). Não há upload persistente pela Files API nem processamento em lote.
A documentação oficial recomenda inline para documentos pequenos/temporários:
[PDF](https://ai.google.dev/gemini-api/docs/generate-content/document-processing),
[Structured Outputs](https://ai.google.dev/gemini-api/docs/generate-content/structured-output),
[SDK oficial](https://github.com/googleapis/python-genai).

## Metadados e falhas

Persistem provider, modelo solicitado/resolvido, data UTC, versão do prompt, status,
ID de resposta, latência e código técnico seguro. `usage_metadata.prompt_token_count`,
`candidates_token_count` e `total_token_count` alimentam `tokens_entrada`, `tokens_saida`
e `tokens_total`. Valores ausentes ficam null. O total é preservado exatamente como
retornado, sem somar ou estimar (pode incluir outros tokens). Confiança não é inventada.

Tratamento controlado: autenticação/permissão (503), quota/rate limit (429), timeout
(504), conexão/indisponibilidade (503), modelo não encontrado (503), arquivo inválido
(422), requisição/schema rejeitados (422), resposta inválida/incompleta/bloqueada (502).
Schema rejeitado é identificado em 400 quando a mensagem cita response_schema ou
response_json_schema; demais 400 permanecem requisição inválida. Corpo, mensagem,
headers e URL do erro Gemini nunca são logados ou persistidos pelo provider.
Uma tentativa por chamada, sem retries ocultos; timeout configurável. Falha não cria
extração parcial, não aprova documento e não apaga extração válida anterior.

A idempotência é compartilhada: bytes iguais reutilizam a extração concluída mesmo
se provider/modelo mudar. Para comparação intencional, use o reprocessamento explícito
já existente; a extração anterior e revisões humanas são preservadas.

## Teste real estritamente manual e privacidade

A partir de `backend/`, somente com documento autorizado e não sensível:

```sh
DOCUMENT_AI_PROVIDER=gemini .venv/bin/python scripts/test_document_ai.py /privado/conta.pdf
DOCUMENT_AI_PROVIDER=openai .venv/bin/python scripts/test_document_ai.py /privado/conta.png --id-usuario 1 --id-prefixo 1
```

A chave deve estar no ambiente privado. O script antigo `scripts/test_openai_document.py`
continua funcionando e também respeita `DOCUMENT_AI_PROVIDER`. Ambos mostram a leitura
com identificadores protegidos, provider/modelo, tokens e latência em metadados. Com IDs,
consultam o contexto para validação determinística; sem IDs reportam evidência contextual
insuficiente. Não gravam extração nem cadastram documento. Relatório sensível completo
continua opt-in via `--relatorio`, arquivo novo com permissão 0600 fora do repositório.

O free tier é adequado somente para desenvolvimento/prototipagem com documentos
autorizados e não sensíveis: conteúdo e respostas podem ser utilizados para melhoria
dos produtos, conforme os [termos oficiais](https://ai.google.dev/gemini-api/terms).
Produção exige avaliação institucional de privacidade e contratação apropriada.
Esta implementação não cria envio automático de documentos institucionais.
Nenhuma chamada real ou documento real foi usado na implementação; a suíte usa fakes.

Limitações: disponibilidade/quota do modelo dependem da conta; qualidade e latência
reais ainda precisam de avaliação manual autorizada. Não há streaming, fila, fallback,
benchmark real ou alteração das regras regionais existentes.

## Validação desta implementação

- 13 testes Gemini novos, incluindo SDK fake, resolver, script genérico e fluxo persistido.
- 73 testes específicos aprovados (Gemini, OpenAI e endpoints documentais).
- Suíte completa: 271 testes aprovados, sem chamadas reais aos providers.
- `pip check` e `git diff --check` aprovados; nenhum padrão de chave nos arquivos envolvidos.
- Frontend, cálculo, contrato de domínio e regras determinísticas não foram alterados.
- Alterações anteriores do workspace preservadas; sem commit, push ou chamada real.
