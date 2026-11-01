# Validação documental e contexto operacional

Esta etapa prepara leitura estruturada e validação determinística. Não integra IA,
OCR novo, autenticação ou mudanças de fórmula. O cálculo continua sem a trava
`resultado_validacao_documental == VALIDO`; o resultado está disponível para
habilitá-la posteriormente.

## Estruturas reutilizadas e novos vínculos

`DadoExtraido` guarda campos descritivos e valores originais/validados.
`ItemExtraido` guarda componentes financeiros; `valor` continua sendo o original.
`ExtracaoInteligente` guarda resultado, motivo, evidências e histórico documental,
separados de `situacao_validacao`, que continua sendo a revisão humana.
`ContaConsumo`, `Documento`, `Prefixo`, `Localidade`, `Concessionaria` e os
repositories existentes continuam sendo utilizados.

Não havia relação equivalente aos vínculos novos:

- `UsuarioPrefixo`: chave composta usuário/prefixo, ativo, principal. Índice único
  parcial permite no máximo um principal ativo; constraint impede principal inativo.
- `UnidadeConsumidora`: prefixo, concessionária, identificador, ativo e endereço
  opcional. Concessionária/identificador é único, inclusive entre prefixos.
  Uma instalação possui um único vínculo cadastral neste MVP. Mudanças de titularidade
  ou compartilhamento exigirão política própria numa próxima etapa.

Usuários com `situacao=ativo` são operacionais. Criação/ativação exige vínculo ativo;
os serviços impedem remover o último vínculo ou desativar o último prefixo efetivo.
Usuários não ativos podem existir como cadastro incompleto e não podem operar.
A migration copia o vínculo legado quando existe, sem inventar prefixos para cadastros
antigos incompletos. Esses cadastros precisam ser saneados e não são autorizados a operar.
A coluna legada `Usuario.id_prefixo` permanece: seleção de um novo principal a sincroniza;
limpá-la não remove os vínculos normalizados. A autorização consulta exclusivamente
os vínculos normalizados e o estado ativo do usuário e do prefixo.

## Contrato e persistência

`LeituraDocumental` é independente de fornecedor. Campos opcionais incluem todos
os dados comuns, de energia e água do escopo. `concessionaria` aceita nome ou CNPJ
cadastrado, com comparação textual determinística; não existe inferência por marca.
Tipos reconhecidos: `ENERGIA`, `CONTA_ENERGIA`, `AGUA`, `CONTA_AGUA`,
`AGUA_SANEAMENTO`. Tipo ausente/indeterminado requer evidência; outros tipos
explicitamente identificados são documentos não suportados.

`consumo_kwh`/`consumo_m3` convergem para `consumo` e `unidade_consumo`; valores
contraditórios são rejeitados. `valor_total` converge para `valor_original`, mantendo
a integração com o cálculo atual. `numero_documento` permanece campo extraído, sem
presumir equivalência com `ContaConsumo.numero_conta`. Bandeira descritiva fica em
`DadoExtraido`; `valor_bandeira_tarifaria`, se informado, vira componente `BANDEIRA`.
Os componentes financeiros usam a estrutura atual de itens, sem duplicação em campos.

Nova interpretação cria outra extração e preserva as anteriores. Processar novamente
um documento retorna a extração concluída mais recente; não cria nova extração.

## Regras documentais

`UF_MVP=PE` configura o escopo. As demais UFs são apenas reconhecidas para rejeição
regional; isso não constitui suporte operacional nacional.

1. Tipo explicitamente diferente de energia/água: `DOCUMENTO_NAO_SUPORTADO`.
2. Tipo/UF não confirmados: `EVIDENCIA_INSUFICIENTE`.
3. Conta de energia/água com outra UF brasileira identificada: `REGIAO_NAO_SUPORTADA`.
4. Contexto não informado, ambíguo ou revogado: `EVIDENCIA_INSUFICIENTE`.
5. Município/UF divergentes do prefixo: `DIVERGENCIA_PREFIXO`.
6. Concessionária não identificada univocamente ou unidade sem cadastro ativo:
   `EVIDENCIA_INSUFICIENTE`.
7. Unidade comprovadamente cadastrada em outro prefixo: `DIVERGENCIA_PREFIXO`.
8. Tipo, região, usuário, localidade e unidade compatíveis: `VALIDO`.

Em requisições com contexto explícito, prefixo não autorizado é rejeitado com HTTP 403
antes de leitura/persistência. O validador não aceita uma decisão de autorização do
mecanismo de leitura. Identificador de unidade usa comparação exata, preservando
zeros à esquerda; endereço livre não confirma vínculo.

## Endpoints

Todos sob `/api/v1`:

- `PUT /usuarios/{id}/prefixos`: substitui o conjunto de vínculos, preservando registros
  anteriores como inativos. Corpo: `{"vinculos":[{"id_prefixo":1,"ativo":true,"principal":true}]}`.
- `GET /usuarios/{id}/prefixos`: consulta vínculos, inclusive inativos.
- `POST /unidades_consumidoras`: cadastra vínculo de instalação.
- `GET /unidades_consumidoras`: consulta cadastro.
- `PATCH /unidades_consumidoras/{id}`: modifica atividade/endereço de referência.
- `POST /documentos/{id}/interpretacao`: entrada estruturada simulada ou de futuro
  adaptador. Corpo com `leitura` e `contexto` (`id_usuario`, `id_prefixo` opcional).
- `POST /extracoes_inteligentes/{id}/revalidar`: corpo com contexto operacional.
- Upload e processamento existentes aceitam `id_usuario`/`id_prefixo` como query.
  Com um único prefixo ativo, seleção é automática; com vários, é obrigatória.
  O principal não substitui seleção quando há múltiplos vínculos.

Identidade ainda é declarada, não autenticada. A dependência `get_contexto_operacional`
é o ponto de substituição pelo futuro principal autenticado. Os endpoints cadastrais
continuam com o modelo de acesso existente. Este mecanismo não fornece segurança
contra alguém que declare a identidade de outro usuário: autenticação permanece
fora do escopo.

Por compatibilidade, upload/processamento sem contexto continuam extraindo pelo
fluxo legado; uma nova extração sem contexto nunca recebe `VALIDO`. Informar somente
`id_prefixo` sem usuário é rejeitado. O contexto deve acompanhar cada operação.
O extrator determinístico atual continua limitado e não foi ampliado para classificar
contas reais; a nova entrada estruturada permite testar integralmente o contrato.

## Revisão, revalidação e auditoria

`PATCH /dados_extraidos/{id}` só permite tornar a revisão pendente. Não aceita
`valor_extraido`, `campo_identificado`, `id_extracao` ou correção de valor.
Correções usam `/dados_extraidos/{id}/validacao`; itens mantêm sua validação própria.
O schema interno legado de update continua disponível aos repositories, mas o
service também impede alterar a identidade/original de um dado já revisado.

Correção de tipo, UF, município, concessionária, unidade ou endereço reexecuta a
validação na mesma transação. Usa `valor_validado` quando o campo está validado;
caso contrário, usa o extraído. Valores financeiros não alteram decisão territorial.
Mudanças cadastrais nos serviços de conta, documento, extração, prefixo, localidade,
concessionária, usuário, vínculos ou unidade revalidam contextos persistidos.
Revalidação explícita pode trocar o usuário/contexto, após autorização.

Cada revalidação acrescenta resultado, motivo, horário UTC e snapshot dos dados,
origem extraída/validada, IDs cadastrais e versão do validador. O histórico anterior
não é apagado. Ele reside no JSON da extração para evitar outra entidade nesta etapa.
O MVP revalida contextos de forma síncrona; volume maior exigirá filtragem de
impacto e eventual processamento assíncrono. O histórico JSON também poderá migrar
para armazenamento de auditoria dedicado conforme volume/retenção.

## Migration e verificação

Migration aditiva: `8bd731c29a10_contexto_validacao_documental.py`, após
`e172d1b499a0`. Adiciona tabelas e colunas; não remove dados nem colunas existentes.
Foi aplicada no PostgreSQL configurado. O teste de migration também executa toda a
cadeia em SQLite temporário, verifica backfill e restrição de principal único.

Comandos, a partir de `backend/`:

```sh
.venv/bin/alembic upgrade head
.venv/bin/python -m unittest tests.test_validacao_documental tests.test_contexto_documental_api tests.test_migration_documental
.venv/bin/python -m unittest discover -s tests
```

Resultado final: **198 testes executados, 198 aprovados**, sendo **61 testes novos**.
Os 61 testes novos também foram executados separadamente e aprovados.
`git diff --check` passou; `git status --short` foi executado.

Os testes HTTP precisaram executar fora do sandbox restrito. Os testes usam bancos
isolados; a suíte não usa o PostgreSQL operacional para seus cenários.

## Inventário da implementação

Criados:

- `app/models/usuario_prefixo.py`
- `app/models/unidade_consumidora.py`
- `app/schemas/leitura_documental.py`
- `app/schemas/vinculos.py`
- `app/services/contexto_operacional.py`
- `app/services/interpretacao_documental.py`
- `app/services/validacao_documental.py`
- `app/api/routes/contexto_documental.py`
- `migrations/versions/8bd731c29a10_contexto_validacao_documental.py`
- `tests/test_validacao_documental.py`
- `tests/test_contexto_documental_api.py`
- `tests/test_migration_documental.py`
- `VALIDACAO_DOCUMENTAL.md`

Modificados:

- `.env.example`
- `app/core/config.py`
- `app/main.py`
- `app/models/__init__.py`
- `app/models/usuario.py`
- `app/models/extracao_inteligente.py`
- `app/schemas/dado_extraido.py`
- `app/schemas/extracao_inteligente.py`
- `app/services/base.py`
- `app/services/usuario.py`
- `app/services/prefixo.py`
- `app/services/localidade.py`
- `app/services/concessionaria.py`
- `app/services/conta_consumo.py`
- `app/services/documento.py`
- `app/services/extracao_inteligente.py`
- `app/services/dado_extraido.py`
- `app/services/processamento_documento.py`
- `app/services/exceptions.py`
- `app/repositories/extracao_inteligente.py`
- `app/api/__init__.py`
- `app/api/dependencies.py`
- `app/api/routes/__init__.py`
- `app/api/routes/conta_consumo.py`
- `app/api/routes/documento.py`
- `app/api/routes/dado_extraido.py`
- `tests/test_api.py`
- `tests/test_api_integration.py`

As mudanças dos dois testes existentes refletem campos adicionais nas respostas e a
migração das correções para o endpoint próprio. Testes de cálculo não foram alterados.
Alterações prévias em `MVP_DEMO.md`, arquivos de demonstração e arquivos fora do
backend foram preservadas; não integram esta implementação.

## Decisões antes da integração de leitura real

- Definir identidade autenticada e autorização dos cadastros/revisores.
- Sanear vínculos legados e cadastrar concessionárias e unidades autorizadas.
- Definir a política de aliases/identificadores de concessionária e formatação da
  unidade, evitando comparações aproximadas como autorização automática.
- Definir limites de confiança e revisão para evidências de leitura automática.
- Definir quando ativar a trava documental do cálculo e sua transição para contas legadas.
- Definir retenção/escala do histórico e casos de transferência/compartilhamento de instalação.
