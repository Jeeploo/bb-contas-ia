# Jornada documental DEMO

A demonstração passa por upload, leitura, conferência humana, validação, cálculo, resultado, processamento concluído e Checker. Não houve alteração de infraestrutura ou esquema do banco, commit, push ou deploy.

## Bloqueios e alertas

Continuam bloqueando arquivos inválidos, documentos não suportados, região fora do escopo, campos documentais essenciais ausentes ou inválidos, divergências comprovadas de prefixo/contexto e falhas técnicas. Tipo documental, UF, município, nome documental da concessionária, unidade consumidora, competência, vencimento e valor continuam obrigatórios. Nome documental ausente não equivale a ausência de correspondência cadastral.

Concessionária sem correspondência (inclusive alias ausente ou ambíguo), unidade sem vínculo ativo e cadastro incompleto de tipo de serviço passam a ser alertas não bloqueantes. Os dois primeiros podem coexistir. Os dados originais permanecem preservados, e a associação manual continua disponível, opcional, na etapa 3.

Erros aparecem em vermelho; pendências cadastrais em amarelo, com “Pendência que não impede continuar”; informações em azul. O envio exige confirmação humana e a decisão determinística do backend.

## Cálculo e conclusão

O cálculo documental utiliza o mesmo motor financeiro do cálculo por conta: perfil do prefixo vigente na competência confirmada, regra ativa e vigente, estratégia, parâmetros, componentes obrigatórios e arredondamento Decimal. As estratégias integral, coeficiente e composição detalhada permanecem disponíveis.

Quando falta correspondência cadastral, usa-se a configuração existente do prefixo e o serviço identificado e confirmado no documento. A memória registra a origem da regra, a falta de correspondência e as pendências. Nenhum coeficiente, componente, concessionária ou unidade é criado como substituto. Perfil/regra inexistente, incompatibilidade financeira conhecida, parâmetro inválido ou componente obrigatório ausente continuam impedindo cálculo.

Para o documento real, foi configurada a **Regra DEMO — Coeficiente 0,9055**, exclusivamente no prefixo **7**, competência **2026-09**: perfil **4**, regra **5**, vigência de 01/09/2026 a 30/09/2026. O cadastro mínimo contém o coeficiente como string decimal e metadados explícitos de demonstração e escopo. Outros perfis/regras permanecem intactos.

A fórmula é **valor_original / 0.9055**, com Decimal e `ROUND_HALF_UP`: **736.53 / 0.9055 = 813.40**, diferença **76.87**. A memória persiste nome da regra, coeficiente, divisão, expressão, resultado antes/depois de arredondar, diferença e aviso. A interface apresenta esses valores persistidos, sem subtração monetária com float.

Aviso exibido: “Regra demonstrativa baseada em um caso real de prefixo específico. Não representa uma regra financeira aplicável a todos os prefixos do Banco do Brasil.” O motor recusa o uso dessa configuração demonstrativa fora do prefixo ou competência definidos.

A configuração pode ser reproduzida com `cd backend` e `.venv/bin/python -m scripts.configurar_regra_demo --documento 27`. O script é idempotente, não sobrescreve um perfil financeiro vigente e não chama IA. Uma simulação somente leitura usando a configuração real confirmou o resultado de R$ 813,40, sem alterar a validação humana da fatura.

O resultado documental DEMO é persistido como evento `CALCULO_DEMO` no histórico JSON já existente da extração, com valores, memória, usuário e data. Ele tem identificador da extração, sem inventar um ID de registro da tabela de cálculos ou exigir conta com concessionária fictícia. Cálculos do caminho anterior podem ser recuperados quando a memória os vincula à extração exata.

Após sucesso, a extração recebe `processamento_concluido`; contas existentes recebem `pronta_checker`. A tela mostra valor original confirmado, valor final, diferença e memória da regra aplicada. Repetir a solicitação recupera o resultado persistido. Alterações de dados após conclusão não sobrescrevem silenciosamente o cálculo conferido.

## Retomada e Nova fatura

`GET /documentos/jornada/atual` consulta a última jornada do usuário e prefixo ativo no backend. Reconstrói documento, campos originais/normalizados/confirmados, itens, alertas, histórico e cálculo. A consulta não instancia o provedor de IA, não chama Gemini e não exige novo upload. Extrações legadas são reavaliadas deterministicamente com a política atual.

O stepper deriva desses dados: documento sem leitura na etapa 1, resumo na 2, envio/validação na 3, cálculo válido na 4. Navegar para Faturas e retornar, ou recarregar a página, preserva o estágio. Se a consulta falhar, aparece uma ação de recuperação; a tela não oferece upload enquanto desconhece a jornada existente. A seleção de prefixo continua disponível quando existem múltiplos vínculos sem seleção ativa.

“Nova fatura” registra o encerramento do contexto visual. Não exclui documento, extração, cálculo ou histórico, nem retoma indevidamente uma jornada anterior. Upload ainda sem leitura também pode ser encerrado.

## Checker

A navegação inclui Checker em `/aprovacoes`, junto ao fluxo de aprovações existente. A fila documental consulta `GET /documentos/jornada/checker` por prefixo autorizado. Exibe documento original, valores extraídos e confirmados lado a lado, itens, cálculo, memória e pendências.

A decisão registra `DECISAO_CHECKER`, usuário, observação e data; a situação final é `confirmada_checker` ou `rejeitada_checker`. Autoaprovação permanece proibida, aprovação exige alçada suficiente e nova decisão sobre a mesma conclusão é recusada. O documento é servido por endpoint autenticado, respeitando o escopo de prefixo e o armazenamento já configurado.

## Validação

- Backend: `python -m unittest discover -s tests` com o Python da virtualenv: **383 testes aprovados**; cobertura de bloqueios reais, alertas coexistentes, cálculo, idempotência, retomada sem IA, isolamento por usuário/prefixo, Nova fatura, compatibilidade legada, associação opcional e Checker.
- Frontend: `npm test` (19 testes aprovados), `npm run lint` e `npm run build` aprovados.
- Integridade: `git diff --check`.
- Navegador: `frontend/review/journey-demo.cjs` usa `frontend/review/journey-server.py`, com SQLite/storage temporários, autenticação substituída exclusivamente nesse servidor de teste e replay da leitura real recuperada em consulta somente leitura ao banco operacional.

O PDF real da COMPANHIA ENERGÉTICA DE PERNAMBUCO foi usado no navegador com sua leitura persistida. O teste percorreu upload, resumo, correção de consumo, validação, cálculo integral explicitamente configurado no banco de teste, resultado de R$ 736,53 e conclusão. Percorreu Pagamentos → Faturas → Pagamentos nas etapas 2, 3 e 4 e recarregou a página na etapa 3. Um upload e um replay, zero chamadas Gemini, com retomadas adicionais pelo backend. Nova fatura preservou a fila do Checker; a autoaprovação foi recusada e outro usuário confirmou a fatura. Também passaram os casos de múltiplos prefixos sem seleção inicial e falha temporária da retomada seguida de recuperação, mantendo o upload indisponível até conhecer o estado do backend.

Snapshots e capturas com dados documentais ficam em `/tmp`, fora dos arquivos versionados.

## Limites

A revisão no navegador usa ambiente isolado e a mesma regra DEMO explicitamente autorizada; não executa uma nova leitura externa. No banco DEMO real foram criados somente a regra e o perfil mínimos do prefixo/competência informados, conforme solicitado. A confirmação dos campos e a decisão do Checker no documento operacional continuam sendo ações humanas da interface. O cálculo continua exigindo configuração financeira válida existente. O resultado documental DEMO e sua decisão ficam no histórico da extração e não geram ordem bancária ou pagamento real. Não foi aplicada migração nem realizado deploy.
