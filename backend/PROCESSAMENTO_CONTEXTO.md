# Etapa 6A: processamento e cálculo por contexto

Prefixo → PerfilProcessamento → tipo de serviço / estratégia / RegraCalculo →
PDF textual ou OCR local → extração estruturada → validação humana → motor → Calculo.

O Prefixo continua relacionado à Localidade (município/UF). Perfis próprios permitem
histórico por vigência sem alterar cadastros existentes. Cada perfil contém estratégia,
regra, concessionária esperada opcional, situação, início/fim e parâmetros JSON.
Tipos de serviço são strings extensíveis (energia, agua, condominio etc.). Não há lógica
por UF, código de Prefixo ou fornecedor. Perfis ativos sobrepostos são rejeitados pelo
service; o motor também rejeita contexto ausente ou ambíguo.

A competência **validada**, no formato AAAA-MM, define a data de referência (dia 1)
para a vigência inclusiva do perfil e da regra. O motor usa a extração mais recente da
conta, ordenada por processamento e ID; não combina documentos distintos. Perfil,
regra e serviço precisam ser compatíveis, e a concessionária esperada precisa coincidir.
Sem perfil/regra, upload, extração e validação continuam disponíveis; cálculo retorna 422.

## Estratégias e configuração

- `VALOR_INTEGRAL`: total validado, sem acréscimos.
- `COEFICIENTE`: total validado / coeficiente. Configure `parametros` como
  `{"coeficiente":"0.85","arredondamento":"ROUND_HALF_UP"}`. Strings decimais
  preservam precisão; coeficiente deve ser finito e maior que zero, inclusive abaixo de 1.
- `COMPOSICAO_DETALHADA`: os ItemRegra da regra definem `nome_item` como tipo
  normalizado (`TUSD`, `TE` etc.), `tipo_item` como `SOMAR` ou `DESCONTO`,
  `obrigatorio` (padrão true) e `ordem_aplicacao`. Descontos usam magnitude positiva.
  Componentes repetidos na fatura são somados; configurações repetidas são rejeitadas.
  Componentes opcionais ausentes contribuem zero; componentes fora da regra são ignorados.
  Não existe fórmula bancária implícita nem uso de `valor_percentual` nesta estratégia.

A aritmética usa Decimal e arredonda **apenas o resultado final**, em centavos,
com ROUND_HALF_UP. 10000 / 0.85 resulta 11764.71; 1.01 / 2 resulta 0.51.
Resultados negativos, não finitos ou fora de Numeric(14,2) são rejeitados.
Competência e valor_original devem estar validados em todas as estratégias.
Na composição, todos os componentes presentes utilizados pela regra também devem
estar validados, mesmo opcionais. Confiança alta sozinha nunca autoriza cálculo.

## Extração e validação

`StructuredDocumentExtractor` recebe texto e contexto do Prefixo e retorna campos
mais itens tipados. A implementação atual é determinística e local, após pypdf/OCR
Tesseract. O FieldExtractor antigo permanece disponível para integração existente.
Uma futura IA estruturadora poderá implementar o mesmo contrato sem mudar banco,
API ou motor. OCR/IA lê a conta; humano valida; regra vem do cadastro; motor calcula.
**IA não decide pagamento.** Aprovação e maker/checker continuam no fluxo existente.

`ItemExtraido` representa componentes e tributos (`categoria=tributo`), incluindo
quantidade, unidade, valor unitário, base e alíquota quando explícitos no texto.
Os campos originais `campos_encontrados` permanecem; o processamento adiciona
`itens_encontrados`. A confirmação/correção grava somente valor_validado e situação,
preservando descrição/valor extraído/confiança. Não há PATCH genérico de itens.

Aliases iniciais: Consumo-TUSD / TUSD / USO SIST. DISTR. (TUSD);
Consumo-TE / TE / ENERGIA (TE); bandeira / bandeira amarela / bandeira vermelha;
iluminação pública / contribuição iluminação pública / CIP; ICMS, PIS, COFINS;
desconto/descontos. Acentos, pontuação e maiúsculas são normalizados.
Aliases adicionais podem ser injetados no extrator.

Rótulos de campos podem usar `:`, `|`, espaços múltiplos ou valor na linha seguinte.
Itens aceitam descrição e valor, ou tabelas com `|` / espaços múltiplos:
`Consumo-TUSD | 523 kWh | 0,72428200 | 378,79` e
`ICMS | 659,05 | 18,00% | 118,63`.
Não há coordenadas nem dependência de posição na página. Layouts ambíguos,
linhas desconhecidas, tabelas com colunas extras ou OCR fragmentado podem exigir
tratamento manual ou evolução do extrator. Não é um parser universal de faturas.

## API

- CRUD `/api/v1/perfis_processamento` para contexto por Prefixo.
- GET `/api/v1/itens_extraidos` e `/{id}` para inspeção dos componentes.
- PATCH `/api/v1/itens_extraidos/{id}/validacao`: `{}` confirma; um
  `{"valor_validado":"380.00"}` corrige. Null explícito é rejeitado.
- POST `/api/v1/contas_consumo/{id_conta}/calcular`: sem fórmula nem body;
  retorna 201 com Calculo e `memoria_calculo` persistida. Falhas de contexto/validação
  retornam 422 e não persistem cálculo; conta inexistente retorna 404.

Memória inclui estratégia, perfil/regra/versão, competência, extração, localidade,
valor base, parâmetros, itens da regra, componentes considerados/ignorados,
resultado antes e depois do arredondamento. Valores monetários são strings no JSON.
Cada chamada bem-sucedida cria um novo cálculo histórico. Não cria ordem nem pagamento.
Os CRUD antigos de cálculo continuam manuais por compatibilidade; o endpoint novo é
quem aplica o bloqueio por validação e resolve a estratégia automaticamente.

## Migração, demonstração e limites

Migration `e172d1b499a0` adiciona somente perfis_processamento, itens_extraidos,
itens_regra.obrigatorio (default true para registros anteriores) e calculos.memoria_calculo
(nullable para histórico). Nenhuma migration anterior é alterada.

`backend/scripts/seed_demo.py` mantém a demonstração anterior e prepara três novos
Prefixos fictícios com contas: coeficiente, composição predial e integral. A composição
fictícia inclui TUSD+TE, bandeira opcional e desconto opcional; não é fórmula real.
O seed consulta antes de criar, preserva registros existentes e não executa validação,
cálculo automático, aprovação ou pagamento. Pode ser repetido com o mesmo cenário.

Somente backend nesta etapa. A visualização e edição destes cadastros/componentes no
desktop ficam para 6B. Sem provedores externos, autenticação ou integrações bancárias.

## Arquivos desta evolução

Criados (caminhos relativos a `backend/`):

- `app/models/perfil_processamento.py`, `app/models/item_extraido.py`
- `app/schemas/perfil_processamento.py`, `app/schemas/item_extraido.py`
- `app/repositories/perfil_processamento.py`, `app/repositories/item_extraido.py`
- `app/services/perfil_processamento.py`, `app/services/item_extraido.py`, `app/services/calculo_contextual.py`
- `app/api/routes/perfil_processamento.py`, `app/api/routes/item_extraido.py`
- `app/calculation/__init__.py`, `app/calculation/strategies.py`
- `app/processing/structured.py`
- `migrations/versions/e172d1b499a0_perfil_processamento_itens_extraidos_.py`
- `tests/test_6a.py`, `PROCESSAMENTO_CONTEXTO.md`

Alterados nesta etapa (caminhos relativos a `backend/`):

- `app/models/__init__.py`, `app/models/calculo.py`, `app/models/extracao_inteligente.py`, `app/models/item_regra.py`
- `app/schemas/calculo.py`, `app/schemas/item_regra.py`, `app/schemas/processamento_documento.py`
- `app/services/exceptions.py`, `app/services/processamento_documento.py`
- `app/api/__init__.py`, `app/api/routes/__init__.py`, `app/api/routes/conta_consumo.py`
- `scripts/seed_demo.py` (já existia como arquivo não versionado da demonstração)
- `tests/test_api.py`, `tests/test_api_integration.py`, `tests/test_schemas_calculo.py`

As três expectativas antigas de resposta foram ajustadas apenas para campos adicionais:
obrigatorio=true e memoria_calculo=null em cadastros legados. As verificações originais
foram mantidas. Alterações preexistentes de documentação, frontend, PDFs e demais
scripts da demonstração foram preservadas.

## Validação concluída

- Testes novos isolados: 22 passando (estratégias, layouts, contexto e seed idempotente).
- Suíte completa: 137 passando, incluindo os 115 testes existentes.
- `alembic upgrade head` aplicado no PostgreSQL local.
- `alembic current`: `e172d1b499a0 (head)`.
- `alembic check`: `No new upgrade operations detected.`
- `git diff --check`: sem erros.
- Nenhum commit ou push realizado.
