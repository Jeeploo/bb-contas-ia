> OpenAI continua disponível e padrão. Para seleção de provider, configuração Gemini e privacidade, consulte [LEITURA_GEMINI.md](LEITURA_GEMINI.md). O script antigo também respeita `DOCUMENT_AI_PROVIDER`.

# Leitura documental com OpenAI

## Arquitetura e escopo

A nova leitura inteligente usa OpenAI como único provider implementado:

```
PDF/JPEG/PNG → DocumentAIProvider → OpenAIDocumentAIProvider
→ Structured Outputs → normalização → LeituraDocumental
→ InterpretacaoDocumentalService → persistência atômica
→ ValidacaoDocumentalService → resultado documental
```

Não há consulta de cadastros nem envio de UF, município, prefixo, perfil, usuário ou
unidade esperada ao provider. Ele recebe somente o arquivo e instruções de extração.
A decisão permanece determinística e aceita operacionalmente apenas `UF_MVP=PE`.
A identificação de outra UF serve para rejeição regional, não roteamento nacional.

`POST /api/v1/documentos/{id}/processar-inteligente?id_usuario=...&id_prefixo=...`
é a nova entrada principal de IA. Exige contexto autorizado antes de enviar o arquivo.
Com um único prefixo ativo, `id_prefixo` pode ser omitido. Não existe autenticação nova:
a identidade continua declarada como na etapa anterior e precisa ser substituída por
identidade autenticada no futuro. Cadastros/autorização seguem no backend.

O endpoint legado `/processar` e seu extrator/OCR continuam disponíveis. Ele não é
fallback automático: falha OpenAI retorna erro controlado, sem chamar outro extrator.
As fórmulas e a ativação da trava documental do cálculo não foram alteradas.

## SDK, API e configuração

Dependência direta adicionada: **openai==2.54.0**, SDK oficial Python, inspecionado
localmente. Novas dependências transitivas instaladas: distro 1.9.0, jiter 0.18.0,
sniffio 1.3.1 e tqdm 4.70.1. As bibliotecas de imagem/PDF já existiam.

Usa `OpenAI.responses.create`, com `text.format.type=json_schema`, `strict=true` e
`store=false`. Não usa Assistants, texto livre, ferramentas, treinamento nem frameworks.
`max_retries=0` impede novas cobranças/tentativas ocultas em falhas transitórias.

No ambiente privado do backend, configure:

```dotenv
OPENAI_API_KEY=
OPENAI_DOCUMENT_MODEL=
OPENAI_DOCUMENT_TIMEOUT=90
OPENAI_DOCUMENT_MAX_OUTPUT_TOKENS=6000
UF_MVP=PE
```

Preencha os dois primeiros valores somente no ambiente privado. O `.env.example`
permanece sem segredo. Não há modelo padrão: configure explicitamente um modelo
habilitado na sua conta que aceite PDF/imagem e Structured Outputs. Ausência de
modelo/chave falha de forma controlada, sem troca silenciosa de modelo.

Fontes oficiais consultadas:

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Images and vision](https://developers.openai.com/api/docs/guides/images-vision)

## Arquivos e Structured Outputs

PDF é enviado como `input_file`, com nome genérico `documento.pdf` e Data URL base64.
JPEG/PNG são enviados como `input_image`, Data URL base64 e `detail=high`.
Não há upload persistente na Files API nem URL pública para o documento.
O conteúdo necessariamente é transmitido à OpenAI; `store=false` não substitui os
termos de retenção, governança ou configuração da conta contratada.

Upload valida extensão/MIME e conteúdo. Aceita `.pdf`, `.jpg`, `.jpeg`, `.png`.
`application/octet-stream` é aceito somente para PDF, por compatibilidade existente.
Imagens são verificadas com Pillow, inclusive formato real e limite de 40 milhões
de pixels. O limite de bytes existente continua valendo (10 MiB por padrão).
Na nova leitura, PDF também é aberto com pypdf para rejeitar arquivo inválido,
protegido ou sem páginas antes do envio. Não foi implementado novo OCR.

O schema é gerado de `LeituraDocumental.model_json_schema(mode='serialization')`.
Um adapter interno remove defaults, torna todas as propriedades obrigatórias porém
nullable e fecha propriedades extras. Decimais são strings, preservando precisão.
Apenas o campo de classificação é restrito no schema de transporte:
`CONTA_ENERGIA`, `CONTA_AGUA`, `OUTRO` ou null. Não existe segundo DTO de negócio.
Após conferir status/recusa/conteúdo, JSON é decodificado e validado por Pydantic.
Não se tenta extrair JSON de uma resposta em texto livre.

O prompt instrui a usar somente evidência visível, ignorar comandos dentro do
arquivo, não inferir UF pelo fornecedor, preservar identificadores/zeros, separar
consumo de dinheiro e tributos de tarifas, e deixar campos ausentes como null.
Documento ambíguo permite tipo null → `EVIDENCIA_INSUFICIENTE`; documento identificado
como boleto/comprovante/nota/extrato/contrato é `OUTRO` → `DOCUMENTO_NAO_SUPORTADO`.

Todos os campos comuns, de energia e água da etapa anterior estão no mesmo contrato.
A normalização aceita formatos explícitos brasileiros de dinheiro/data, remove
espaçamento redundante, padroniza UF/unidades e remove somente separadores permitidos
do código de barras. Não faz fuzzy matching ou preenchimento de dados ausentes.
Código incompleto/ilegível é inválido, não é completado.

## Persistência, originais, auditoria e idempotência

A migration aditiva `b21d94ca730e_metadados_leitura_ia.py` acrescenta:

- `Documento.historico_leitura_ia`: tentativas com status/metadados técnicos, inclusive erros.
- `ExtracaoInteligente.metadados_ia`: provider, modelo solicitado/retornado, response ID,
  horário UTC, status, versão do prompt, latência, tokens reais e SHA-256 dos bytes.
- `ExtracaoInteligente.resposta_original_ia`: payload interpretado original, sem o PDF.
- `DadoExtraido.valor_normalizado`: representação canônica utilizada pelo backend.

Não foi criada outra entidade. Os metadados são expostos na resposta da nova leitura;
`GET /api/v1/documentos/{id}/leituras-ia` consulta tentativas após validar o contexto.
As respostas legadas mantêm o formato da etapa anterior.

`valor_extraido` preserva o conteúdo retornado pelo provider (inclusive diferenças
lexicais); `valor_normalizado` guarda o correspondente normalizado. `valor_validado`
continua sendo confirmação/correção humana. O validador prioriza correção válida,
depois normalizado, depois original legado. Confirmar sem fornecer correção copia o
valor normalizado quando existir. Nos itens financeiros `valor` segue sendo original
numérico; o payload original preserva a representação textual.

Não há confiança percentual artificial. Confiança de extrações/campos/itens da nova
leitura fica null. Tokens são usage real; sem usage, ficam desconhecidos. Não há
estimativa de tokens, preço comercial ou custo calculado.

O documento é bloqueado durante a operação para serializar processamento concorrente.
Sem `reprocessar=true`, os mesmos bytes retornam a última extração IA concluída,
sem nova chamada e preservando revisão humana. Mudança de modelo isoladamente não
força cobrança/reprocessamento. Novo arquivo com bytes diferentes exige nova interpretação.
`reprocessar=true` cria uma nova extração; não copia automaticamente revisões anteriores
nem modifica a extração antiga. A continuidade usa a extração mais recente segundo a
política já existente. Falha não cria extração vazia que substitua uma anterior válida.

## Falhas e logs

São tratados timeout (504), rate limit (429), indisponibilidade (503),
autenticação/permissão/configuração do provider (503), bad request (422),
resposta inválida/vazia/incompleta/recusa (502), arquivo inválido (422), arquivo
indisponível (404) e excesso de tamanho (413). Falhas de upload seguem os erros já
existentes. Erros não geram `VALIDO`, não apagam extrações e não persistem campos parciais.

O corpo/headers/URL de erros SDK não são propagados. Logs próprios contêm somente
ID do documento e código técnico. Não habilite logging de corpo HTTP/`OPENAI_LOG=debug`
em ambientes com documentos. Não há chave, documento integral ou barcode nos logs
próprios. Originais sensíveis ficam no banco, sujeitos à política de acesso/retenção.

## Avaliação real manual

A partir de `backend/`, com variáveis privadas configuradas:

```sh
.venv/bin/python scripts/test_openai_document.py /caminho/privado/conta.pdf
.venv/bin/python scripts/test_openai_document.py /caminho/privado/conta.png --id-usuario 1 --id-prefixo 1
```

Os IDs são exemplos de argumentos; use IDs reais cadastrados/autorizados no seu banco.
O script efetua **chamada real com consumo de API**, mas não cadastra o arquivo nem grava
extração no banco. Com contexto, consulta o banco para decisão determinística; sem
contexto, reporta insuficiência contextual. Ele não faz parte da suíte automática.
A saída mostra campos úteis e uso; omite barcode/endereço/número do documento e mascara
a unidade consumidora. O script real não foi executado contra a API nesta implementação.
Seu fluxo foi testado com provider mockado.

Para preparar a avaliação de 20–50 documentos, opcionalmente:

```sh
.venv/bin/python scripts/test_openai_document.py /privado/conta.pdf --esperado /privado/esperado.json --relatorio /privado/resultado.json
```

O JSON esperado contém um subconjunto dos campos canônicos. O relatório registra
extraído, esperado, igualdade exata por campo, tokens, latência e resultado documental.
`--relatorio` é opt-in explícito: contém dados sensíveis completos e cria arquivo novo
com permissão 0600; não sobrescreve arquivo existente. Mantenha documentos/relatórios
fora do repositório. Ainda não existe agregador de benchmark nem métrica fuzzy.

## Inventário desta etapa

Criados:

- `app/document_ai/__init__.py`
- `app/document_ai/base.py`
- `app/document_ai/normalizacao.py`
- `app/document_ai/openai_provider.py`
- `app/document_ai/prompt.py`
- `app/processing/arquivo_documental.py`
- `app/services/leitura_inteligente.py`
- `app/schemas/leitura_inteligente.py`
- `migrations/versions/b21d94ca730e_metadados_leitura_ia.py`
- `scripts/test_openai_document.py`
- `tests/test_document_ai.py`
- `tests/test_document_ai_api.py`
- `LEITURA_OPENAI.md`

Modificados em relação à fundação aprovada:

- `.env.example`
- `requirements.txt`
- `app/core/config.py`
- `app/api/__init__.py`
- `app/api/routes/documento.py`
- `app/models/documento.py`
- `app/models/extracao_inteligente.py`
- `app/models/dado_extraido.py`
- `app/processing/storage.py`
- `app/services/processamento_documento.py`
- `app/services/interpretacao_documental.py`
- `app/services/validacao_documental.py`
- `app/services/dado_extraido.py`
- `tests/test_migration_documental.py` (consulta o head Alembic atual, mantendo o teste de backfill).

O workspace já continha mudanças da fundação e de demonstração sem commit. Foram
preservadas. Nenhum arquivo de frontend ou fórmula foi alterado nesta etapa.

## Limitações e decisões pendentes

- Escolher modelo habilitado e medir qualidade/latência/tokens em layouts reais.
- Definir limiares de revisão por campo e critérios de aceitação; presença não prova precisão.
- Validar políticas de privacidade, retenção e transmissão de documentos reais.
- Definir momento de ativação da trava documental financeira, sem alterar fórmulas.
- Definir comportamento operacional da seleção entre versões e correções após reprocessamento.
- Dimensionar tempo síncrono, bloqueio de documento e histórico JSON conforme volume.
- Autenticação, fallback automático e suporte a outros estados continuam fora do escopo. Gemini está documentado em LEITURA_GEMINI.md.

## Validação executada

- 57 testes novos executados separadamente e aprovados, sem consumo de API real.
- Suíte completa: 255 testes executados e aprovados, incluindo os 198 anteriores.
- Testes cobrem schema/transporte, PDF/JPEG/PNG, campos, normalização, decisão
  determinística, falhas SDK, tentativas, uso, idempotência, revisões e saída manual mockada.
- Migration `b21d94ca730e` aplicada no PostgreSQL configurado; cadeia de migrations
  também testada em SQLite isolado.
- `pip check` e `git diff --check` aprovados; `git status --short` executado.
- Busca de padrões de chave OpenAI nos arquivos modificados/novos: nenhum encontrado.
  `backend/.env` continua ignorado pelo Git. Nenhum arquivo staged.
- Frontend e arquivos de cálculo sem alterações. Sem commit ou push.
