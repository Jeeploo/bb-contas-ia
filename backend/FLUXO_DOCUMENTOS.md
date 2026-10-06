# Fluxo inteligente de documentos — MVP

Os recursos existentes continuam usando os mesmos models, tabelas e CRUDs.
Repositories executam `flush`, services controlam a transação por operação e
`EntityNotFoundRoute` traduz exceções de domínio em HTTP. Nenhuma migration é necessária.

## Configuração e armazenamento

`DOCUMENT_STORAGE_PATH` define o diretório local (padrão `./storage/documentos`,
relativo ao diretório de execução). `DOCUMENT_MAX_SIZE_BYTES` define o limite
(padrão 10485760 bytes, 10 MiB). O diretório só é criado no primeiro upload aceito.
O `.env.example` documenta a configuração; o `.env` real não foi alterado.

O banco guarda a chave UUID com extensão `.pdf` no campo `caminho_arquivo`, nunca
os bytes. O nome enviado pelo cliente serve apenas para conferir a extensão;
o nome físico é gerado pelo servidor. MIME PDF ou octet-stream, extensão PDF e
assinatura `%PDF-` são exigidos. A leitura estrutural completa ocorre no processamento.
Um arquivo corrompido que tenha assinatura PDF pode ser registrado no upload e
falhar com 400 no processamento. Caminhos legados fora do diretório controlado,
inclusive links simbólicos para fora dele, não são lidos pelo processamento.

Se a escrita do Documento falhar, o service faz rollback e remove o arquivo criado.
Esse mecanismo não torna filesystem e banco uma transação distribuída: uma queda
abrupta do processo pode deixar um arquivo órfão. Não há coleta de órfãos no MVP.
O multipart do framework pode usar arquivo temporário durante o recebimento;
o limite da aplicação é aplicado antes de salvar no storage definitivo.

## Endpoints

- `POST /api/v1/contas_consumo/{id_conta}/documentos/upload`: multipart com campo
  `file`; retorna Documento (201). A conta precisa existir.
- `POST /api/v1/documentos/{id_documento}/processar`: retorna `documento`,
  `extracao`, `campos_encontrados` (incluindo confiança individual),
  `confianca_geral` e `situacao`. Nunca retorna o texto completo do PDF.
- `PATCH /api/v1/dados_extraidos/{id}/validacao`: `{}` confirma `valor_extraido`;
  `{"valor_validado": "130.00"}` corrige o valor. Retorna o dado com situação
  `validada`, preservando `valor_extraido` e `nivel_confianca` originais.
  Correção vazia, null e campos desconhecidos são rejeitados (422).

A validação desse endpoint não atualiza ContaConsumo, não executa pagamento e
não muda automaticamente a situação agregada da extração. Os CRUDs existentes
continuam disponíveis e compatíveis; use o endpoint específico para validar.

## Componentes substituíveis

`ProcessamentoDocumentoService` recebe `DocumentStorage`, `DocumentTextExtractor`
e `FieldExtractor` por injeção no construtor. As implementações padrão são
`LocalDocumentStorage`, `HybridPdfTextExtractor` e `DeterministicFieldExtractor`.
Outra implementação pode substituir esses componentes na composição do service,
sem mudanças em rotas, tabelas ou na orquestração de persistência.

`HybridPdfTextExtractor` chama `PdfTextExtractor` (pypdf) primeiro. Havendo texto,
retorna estratégia `text` sem consultar ou executar Tesseract. Apenas ausência de
camada textual aciona `TesseractPdfOcrExtractor`, que renderiza com PyMuPDF a
300 DPI em RGB e executa Tesseract página a página, retornando estratégia `ocr`.
O resultado interno contém texto, páginas, sucesso, estratégia e confiança base;
a API mantém seu contrato e nunca expõe o texto completo. A estratégia não é
persistida, pois não houve alteração de models ou banco.

`MAX_OCR_PAGES` limita o PDF inteiro submetido ao OCR (padrão 10). O limite é
verificado antes de executar Tesseract; PDFs textuais não estão sujeitos a ele.
Valores menores que 1 são rejeitados. `por` é o idioma principal; se não estiver
instalado, usa `eng`. Se ambos estiverem ausentes, ocorre erro de domínio.
Tesseract deve estar instalado no sistema com os dados de idioma locais.
Há timeout de 60 segundos por página e processamento sequencial em memória.
Não há chamadas externas nem downloads durante processamento.

PDF inválido ou protegido falha na leitura nativa e não aciona OCR. PDF misto com
algum texto nativo usa somente esse texto: não há fallback por página neste MVP.
OCR sem caracteres alfanuméricos exige tratamento manual. Texto reconhecido segue
para o mesmo `FieldExtractor`; ruído de OCR pode impedir identificação conservadora.

## Regras conservadoras

Rótulo e valor precisam estar na mesma linha, separados por `:`. Somente:

| Campo persistido | Rótulos | Formato aceito |
| --- | --- | --- |
| codigo_barras | Código de barras, Linha digitável | 44, 47 ou 48 dígitos, com separadores espaço, ponto ou hífen |
| valor_original | Valor total, Total a pagar | valor brasileiro com duas casas decimais; R$ opcional |
| data_vencimento | Vencimento, Data de vencimento | DD/MM/AAAA, data válida |
| consumo | Consumo | número brasileiro, até três casas, seguido de kWh, m3 ou m³ |
| competencia | Competência | MM/AAAA ou AAAA-MM, mês válido |

Rótulos ignoram caixa e acentuação. Valores são normalizados para representação
numérica decimal, data ISO e competência AAAA-MM. Não há regras por concessionária
ou cálculo de dígitos verificadores de boleto. Identificação de código não autoriza pagamento.
Valores conflitantes ou ocorrências malformadas de um mesmo campo excluem esse campo.
Repetições do mesmo valor normalizado produzem um único resultado.

As confianças base são **95/100 para texto nativo** e **80/100 para OCR**.
São heurísticas fixas do MVP, não probabilidades calibradas nem escores do Tesseract.
O service limita a confiança individual à base da estratégia, preservando escores
inferiores de extratores injetados. A confiança geral é a média dos campos efetivamente extraídos.
Sem campos: confiança geral null, lista vazia e `requer_validacao` para tratamento
manual. Toda extração criada fica `requer_validacao`; dados começam `pendente`.

## Idempotência e transações

Reprocessar retorna a extração existente (200), inclusive quando não há campos,
e conserva correções humanas. Situações concluídas reconhecidas: `processada`,
`requer_validacao`, `validada` e `pendente` (compatibilidade com CRUD legado).
`falha` não impede nova tentativa. Não é usado conflito 409 nesse fluxo.

A linha do Documento é bloqueada com `SELECT FOR UPDATE` no PostgreSQL para
serializar requisições concorrentes desse endpoint. Não há versionamento.
SQLite não oferece esse bloqueio; os testes verificam idempotência sequencial.
Os CRUDs genéricos não participam dessa exclusão de processamento concorrente.

Leitura, identificação e criação de extração/dados pertencem a uma operação com
commit único. Qualquer falha executa rollback e não deixa extração/dados parciais.
Falhas de leitura não criam extração com situação `falha`: a exceção descreve a
falha ao cliente, preservando apenas o Documento previamente enviado. É possível
repetir a tentativa após corrigir a causa. A sessão continua utilizável após rollback.
As datas seguem os models existentes, com UTC sem informação de fuso persistida.

## Exceções HTTP

| Exceção | HTTP |
| --- | --- |
| EntityNotFoundError (existente) | 404 |
| DocumentFileNotFoundError | 404 |
| InvalidPdfError | 400 |
| EmptyDocumentError | 400 |
| UnsupportedDocumentFormatError | 415 |
| DocumentTooLargeError | 413 |
| PdfWithoutTextError (extrator nativo isolado) | 422 |
| TesseractUnavailableError | 503 |
| OcrLanguageUnavailableError | 503 |
| OcrPageLimitExceededError | 413 |
| PdfRenderingError | 422 |
| EmptyOcrError | 422 |
| OcrExecutionError (inclui timeout) | 422 |

## Verificação local

Em `backend`, execute `.venv/bin/python -m unittest discover -s tests -v`.
Os PDFs pequenos são gerados em memória com pypdf, sem fixtures externas.
Os testes usam SQLite e diretórios temporários e verificam inclusive bloqueio
explícito de conexões de rede no upload/processamento, falha real de flush SQL,
rollback de persistência parcial e reutilização da sessão.

Dependências adicionadas: `pypdf==6.19.0` e `python-multipart==0.0.32`.
Após instalar dependências, upload/processamento/testes não precisam de internet.

OCR: `PyMuPDF==1.28.2`, `pytesseract==0.3.13`, `Pillow==12.3.0` e
`packaging==26.3` (as duas últimas dependências do pytesseract). Ambiente validado
com Tesseract 5.3.4 e idiomas `por`, `eng`, `osd`; OCR usa `por` ou fallback `eng`.
Os testes incluem OCR real de PDF rasterizado com rede bloqueada, erros de domínio,
limite, persistência, confiança e rollback SQL com reutilização da sessão.
