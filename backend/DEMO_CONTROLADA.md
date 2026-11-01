# Base DEMO controlada — BB Contas IA

Cadastros, unidades consumidoras e documentos estruturados desta demonstração
são fictícios e identificados como DEMO. As regras executadas são as do backend:
classificação, território PE, autorização de prefixo, vínculo exato da unidade,
correspondência unívoca da concessionária, segregação de autor e alçada.
A apresentação para Renan e Diana não depende de cadastro oficial do BB.

## Preparação local

No diretório `backend`, com dependências, `.env` local e banco já migrado:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Em outro terminal:

```bash
.venv/bin/python scripts/seed_demo.py --ambiente-demo
.venv/bin/python scripts/seed_demo.py --ambiente-demo
```

O sinalizador é obrigatório e confirma que a base é de demonstração. O endereço
da API é fixo em `127.0.0.1:8000`. Não executar contra produção. O seed não chama
Gemini/OpenAI, não exige credenciais de IA e não altera configuração de provider.
Usa a API existente; nenhum schema, migration ou regra de negócio foi alterado.

A repetição reutiliza registros, documentos e extrações, sem duplicar histórico.
Não apaga, não reinicia ordem aprovada e não sobrescreve revisões. Se houver
conflito de cadastro ou resultado revisado diferente da fixture, interrompe e
informa o problema; registros já criados permanecem. Execução é sequencial,
sem promessa de idempotência em concorrência. Para uma nova rodada após revisão
ou aprovação, usar `--cenario ensaio-2` (o nome aceita letras minúsculas,
números e hífen). Isso cria novas contas/documentos/ordem e mantém cadastros.

## Cadastros e vínculos

IDs devem ser obtidos das respostas da API/saída do seed; não são fixos.

| Uso na apresentação | Matrícula reutilizada/criada | Prefixos acrescentados | Alçada |
| --- | --- | --- | --- |
| Maker Recife | DEMO-maker | REC-DEMO | R$ 1.000,00 |
| Maker Paulista | DEMO-maker-paulista | PAU-DEMO | R$ 1.000,00 |
| Maker Multi-Prefixo | DEMO-maker-multi | REC-DEMO e PAU-DEMO | R$ 1.000,00 |
| Checker | DEMO-checker | REC-DEMO e PAU-DEMO | R$ 1.000,00 |
| Alçada reduzida | DEMO-limite-baixo | REC-DEMO | R$ 100,00 |

Os usuários legados mantêm seus nomes fictícios e vínculos, inclusive DEMO e
qualquer vínculo anterior. Não se troca principal existente. Novos usuários
recebem um principal ativo; cada usuário operacional tem ao menos um prefixo
ativo. Havendo múltiplos prefixos ativos, é obrigatório escolher `id_prefixo`,
mesmo existindo um principal.

| Prefixo fictício | Localidade reutilizada | Concessionária | Unidade fictícia |
| --- | --- | --- | --- |
| REC-DEMO | Recife/PE | ENERGIA DEMO PE | UC-REC-ENERGIA-DEMO-001 |
| REC-DEMO | Recife/PE | AGUA DEMO PE | UC-REC-AGUA-DEMO-001 |
| PAU-DEMO | Paulista/PE | ENERGIA DEMO PE | UC-PAU-ENERGIA-DEMO-001 |
| PAU-DEMO | Paulista/PE | AGUA DEMO PE | UC-PAU-AGUA-DEMO-001 |

Localidades são comparadas por município/UF sem diferenças de caixa ou acentos.
Se a base legada já tiver equivalentes duplicados, reutiliza-se o menor ID,
sem criar outra localidade nem mesclar/apagar as existentes. Os prefixos novos
são ativos e fictícios. O prefixo real 0821 é preservado e não é requisito.

As duas concessionárias usam razões sociais/nome fantasia exclusivos e serviço
`energia` ou `agua`. Os identificadores sintéticos `00000000000191` (energia) e
`00000000000272` (água) têm dígitos verificadores matematicamente válidos e raiz
zero de teste; não são dados fiscais obtidos de empresas. Não constituem cadastro
fiscal oficial ou consulta à Receita. A concessionária antiga com CNPJ de zeros
é mantida apenas para compatibilidade dos cenários financeiros anteriores.
Nenhuma concessionária real foi cadastrada para viabilizar a apresentação.

## Cenários e validação rápida

As fixtures estão em `demo/cenarios_documentais.json`. O seed cria contas
`DEMO-DOC-<cenario>-<nome>`, documentos com origem `DEMO estruturada sem IA` e
interpretações pelo endpoint existente:

`POST /api/v1/documentos/{id_documento}/interpretacao`

O corpo contém `leitura` (fixture) e `contexto` com `id_usuario`/`id_prefixo`
resolvidos no cadastro. O seed compara o resultado real ao esperado e imprime
cada caso. Documentos de demonstração referenciam o JSON, não um PDF que possa
ser enviado ao provider. Não usar o endpoint de leitura IA nesta apresentação.

| Fixture/cenário | Resultado esperado |
| --- | --- |
| energia-recife, energia-paulista | VALIDO |
| agua-recife, agua-paulista | VALIDO |
| prefixo-errado (Paulista com contexto Recife autorizado) | DIVERGENCIA_PREFIXO |
| outra-uf (BA) | REGIAO_NAO_SUPORTADA |
| documento-incorreto (boleto) | DOCUMENTO_NAO_SUPORTADO |
| evidencia-insuficiente (sem unidade) | EVIDENCIA_INSUFICIENTE |
| unidade-outro-prefixo (unidade de Paulista em conta Recife) | DIVERGENCIA_PREFIXO |
| concessionaria-desconhecida | EVIDENCIA_INSUFICIENTE |
| multi-recife, multi-paulista (seleção explícita) | VALIDO |
| Maker Recife seleciona PAU-DEMO | Contexto recusado, HTTP 403, sem nova extração |
| Multi-Prefixo seleciona prefixo não vinculado ou omite seleção | Contexto recusado |

Consulta dos vínculos: `GET /api/v1/usuarios/{id_usuario}/prefixos`.
Consulta de unidades: `GET /api/v1/unidades_consumidoras`.
Consulta de decisões/motivos/histórico: `GET /api/v1/extracoes_inteligentes`.
`VALIDO` é resultado documental; os campos permanecem pendentes de revisão humana
(`situacao_validacao` da extração: `requer_validacao`). Não equivale a aprovação
financeira ou pagamento.

Validação automatizada rápida e isolada, sem rede/IA e sem modificar o banco local:

```bash
.venv/bin/python -m unittest tests.test_seed_demo -v
.venv/bin/python -m unittest tests.test_validacao_documental tests.test_aprovacao -v
.venv/bin/python -m unittest discover -s tests -v
```

Os testes novos usam o mesmo seed via TestClient e SQLite com FKs, com rede
bloqueada. Cobrem também concessionária ambígua, unidade inexistente, preservação
integral de registros/históricos na repetição e ausência de persistência após
recusa de prefixo. A suíte completa mantém os testes existentes de OCR e de
providers com clientes simulados; não executar os scripts de leitura real.

## Maker/checker e alçada

O seed mantém o cenário financeiro anterior e imprime o ID de uma ordem
pendente de R$ 123,45 criada pelo `DEMO-maker`. Cálculo/ordem são dados manuais
fictícios do seed; os documentos estruturados novos não disparam cálculo.

Para demonstrar sem consumir a ordem da apresentação, executar:

```bash
.venv/bin/python -m unittest \
  tests.test_seed_demo.DemoSeedTests.test_maker_cannot_approve_own_order \
  tests.test_seed_demo.DemoSeedTests.test_low_limit_cannot_approve \
  tests.test_seed_demo.DemoSeedTests.test_checker_can_approve -v
```

Na API local, `POST /api/v1/aprovacoes` recebe `id_ordem`, `id_usuario`,
`decisao: aprovado` e `data_hora`. Com o autor retorna 409; com o usuário de alçada
R$ 100 retorna 403; com checker de R$ 1.000 retorna 201 e a ordem fica `aprovada`.
Cada teste automatizado prepara banco isolado. Aprovar na API local é uma ação
humana explícita e altera a ordem; o seed não aprova nem reverte a decisão.

A regra existente compara identidade do criador e alçada. `funcao` é cadastral:
não existe papel exclusivo de checker nem autenticação real, e o serviço de
aprovação não adiciona autorização territorial própria. Os vínculos do checker
são preparados para o contexto documental, sem alegar restrições financeiras
que o backend ainda não implementa. A demonstração de maker/processamento ocorre
pela entrada estruturada autorizada; não há simulação de nova leitura paga.

## Resultados já comprovados com leitura real

Gemini já interpretou uma conta real de energia. Identificou tipo documental,
concessionária, município/UF, competência, vencimento, valores, consumo e
componentes tarifários. A unidade completa foi recuperada em relatório privado;
a saída humana permaneceu mascarada. Provider, modelo, tokens e latência foram
registrados, sem reproduzir dados sensíveis nesta documentação.

O backend retornou evidência insuficiente sem contexto cadastral, detectou
corretamente divergência territorial com prefixo de Recife em conta de Paulista
e retornou evidência insuficiente com prefixo de Paulista quando faltou
correspondência cadastral unívoca da concessionária. A extração básica e a
separação entre IA e decisão determinística já foram comprovadas.

Esta etapa usa somente simulações para repetir os estados do backend. Não
cadastra a unidade real, não inventa CNPJ para a concessionária real e não
transforma o documento real anterior em conta DEMO válida.

## Limites antes da apresentação

Sem frontend novo, autenticação, suporte nacional, SISBB ou Plataforma BB.
OpenAI/Gemini, prompts, contrato de leitura e motor de cálculo são preservados.
A preparação requer API local e banco já migrado; não faz migração automática.
Não garante execução simultânea do seed. A base antiga é preservada e pode
conter localidades equivalentes e vínculos extras de ensaios anteriores.
A apresentação documental pode ser feita pela API e pelos testes, sem nova IA.
