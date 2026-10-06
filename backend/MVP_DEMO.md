# Demonstração ponta a ponta do MVP

O cenário usa Recife/PE, uma unidade e uma concessionária de energia fictícias,
CNPJ composto por zeros, matrículas `DEMO-*` e código de barras com 44 zeros.
Nenhum desses dados representa uma conta ou um pagamento real.

A demonstração executável é `tests/test_mvp_flow.py`, pela API com TestClient.
Cada teste cria SQLite em memória com chaves estrangeiras habilitadas e storage
em diretório temporário. O PDF de uma página é gerado em memória pelo helper já
existente em `test_processamento_documento.py`; contém aviso de demonstração,
competência 10/2026, vencimento 20/10/2026, R$ 123,45, consumo 100,500 kWh e código
fictício. Banco e arquivos são descartados ao terminar. Conexões de rede são
bloqueadas durante o cenário. Não há seed nem execução automática em produção.

## Etapas e endpoints

Todos os caminhos abaixo têm prefixo `/api/v1`. IDs vêm das respostas, sem
pressupor valores fixos. Criações retornam 201; consultas e validações, 200.

| Etapa | Endpoint | Resultado demonstrado |
| --- | --- | --- |
| Estrutura | `POST /localidades`, `/prefixos`, `/concessionarias` | Recife/PE e vínculos fictícios |
| Conta | `POST /contas_consumo` | Conta pendente de R$ 123,45 |
| Upload | `POST /contas_consumo/{id}/documentos/upload` | Multipart `file`, Documento e bytes locais persistidos |
| Processamento | `POST /documentos/{id}/processar` | Extração inteligente e cinco dados pendentes, confiança 95/100 |
| Revisão humana | `PATCH /dados_extraidos/{id}/validacao` | Correção do valor para R$ 130,00; demais campos confirmados com `{}` |
| Reprocessamento | `POST /documentos/{id}/processar` | Mesmos IDs, sem duplicação; correções preservadas |
| Regra | `POST /regras_calculo` | Regra demonstrativa sem acréscimos |
| Cálculo manual | `POST /calculos` | Valor inicial e calculado iguais ao valor validado: R$ 130,00 |
| Governança | `POST /sistemas_pagamento`, `/alcadas`, `/usuarios` | Sistema local, maker, checker e terceiro usuário com limite baixo |
| Ordem | `POST /ordens_pagamento` | Vinculada ao cálculo, sistema e maker; pendente, R$ 130,00 |
| Item | `POST /itens_pagamento` | Item da ordem, R$ 130,00; total coerente |
| Autoaprovação | `POST /aprovacoes` com maker | 409; nenhuma aprovação persistida, ordem ainda pendente |
| Alçada insuficiente | `POST /aprovacoes` com limite R$ 129,99 | 403; nenhuma aprovação persistida, ordem ainda pendente |
| Aprovação humana | `POST /aprovacoes` com checker, decisão `aprovado` | Alçada R$ 1.000,00; Aprovacao persistida e ordem `aprovada` |
| Persistência final | `GET /{recurso}/{id}` e listagens | Recursos e vínculos preservados em novas sessões; integridade referencial |

A revisão envia `{"valor_validado": "130.00"}` e verifica que `valor_extraido`
continua `123.45`, a confiança original é preservada e a situação fica `validada`.
O teste representa as ações de pessoas distintas; não cria usuário de IA.

## Execução local

No diretório `backend`, com as dependências de `requirements.txt` instaladas:

```bash
.venv/bin/python -m unittest tests.test_mvp_flow -v
.venv/bin/python -m unittest discover -s tests -v
```

Os dois testes novos comprovam o fluxo completo textual e o fallback de PDF sem
camada textual pela API. No fallback, pypdf e renderização são reais, mas idiomas
e reconhecimento do Tesseract são simulados; a confiança esperada é 80/100.
Os testes existentes em `test_ocr.py` mantêm a demonstração de OCR real com PDF
rasterizado. A suíte completa requer Tesseract e idiomas locais, conforme
[FLUXO_DOCUMENTOS.md](FLUXO_DOCUMENTOS.md).

O próprio teste serve como demonstração repetível para a equipe; não foi criado
um segundo script que duplicaria a orquestração.

## Limitações atuais

- Calculo continua sendo CRUD manual: a demonstração copia explicitamente
  `valor_validado` para `valor_inicial` e `valor_calculado`. RegraCalculo é um
  cadastro vinculado; não há execução de motor financeiro nem de ItemRegra.
- Validar DadoExtraido não atualiza ContaConsumo nem a situação agregada da
  ExtracaoInteligente, que permanece `requer_validacao`. A conta permanece com
  seu valor original; o cálculo usa a correção humana armazenada separadamente.
- Coerência entre valor validado, cálculo, ordem e soma dos itens é comprovada
  pelo cenário, mas não é uma nova restrição automática dos CRUDs.
- Os usuários são identificados pelos IDs enviados no contrato atual. Este teste
  não demonstra autenticação nem autorização de identidade em produção.
- Idempotência é sequencial em SQLite; concorrência PostgreSQL não é avaliada aqui.
- Aprovação é uma ação HTTP explícita simulando o checker. `aprovada` não significa
  pagamento enviado ou liquidado. SistemaPagamento é somente um cadastro, sem
  SISBB, Plataforma BB ou qualquer integração externa.

Models, migrations, regras de aprovação e componentes OCR permanecem intactos.
