# Autenticação DEMO funcional

A tela de acesso agora autentica um dos usuários fictícios existentes. A sessão determina o usuário operacional e o prefixo ativo em Pagamentos; não há seletor manual de identidade nessa jornada. Nome, função e unidade no cabeçalho vêm da sessão.

## Arquitetura e endpoints

Autenticação local, opt-in por `DEMO_AUTH_ENABLED=true`. O padrão de configuração é desabilitado. Não há OAuth, SSO, LDAP, conexão institucional ou MFA real.

Endpoints sob `/api/v1`:

| Endpoint | Comportamento |
| --- | --- |
| `POST /auth/login` | Recebe matrícula, senha e código DEMO; valida hashes e cria sessão. |
| `GET /auth/sessao` | Retorna usuário, prefixos ativos autorizados, principal, ativo e expiração. |
| `PATCH /auth/prefixo` | Altera o prefixo da sessão após verificar autorização. |
| `POST /auth/logout` | Revoga a sessão no banco e remove o cookie. |

O login emite um token aleatório de 32 bytes, em cookie `HttpOnly`, `SameSite=Strict`, com duração absoluta de oito horas e escopo `/api/v1`. O banco guarda somente SHA-256 do token. O token não é devolvido no JSON nem salvo em localStorage. Um novo login revoga a sessão anterior apresentada pelo mesmo navegador. Expiração, logout, remoção da credencial ou usuário inativo invalidam o acesso.

No frontend, o AuthProvider consulta a sessão ao iniciar. Durante a consulta, as telas internas aguardam; sem sessão válida, redirecionam ao acesso. As requisições enviam cookies com `credentials: include`. HTTP 401 encerra o contexto local. Atualizar a página consulta a sessão persistida, sem depender de uma flag visual de login.

## Modelos e proteção das credenciais

Migration `d45f3a21b001`, aplicada ao PostgreSQL local:

- `CredencialDemo` / `credenciais_demo`: `id_usuario`, `senha_hash`, `fator_hash`.
- `SessaoDemo` / `sessoes_demo`: `token_hash`, `id_usuario`, `id_prefixo`, `expira_em`.

Senha e código DEMO usam scrypt (`N=16384`, `r=8`, `p=1`), salt aleatório de 16 bytes e comparação de resultado em tempo constante. Nenhuma coluna de senha em texto puro foi adicionada ao usuário. As credenciais não são expostas pelos schemas cadastrais. Erros de validação dos endpoints de autenticação removem os inputs recebidos, evitando refletir senhas/códigos em respostas de erro. Não foram adicionados logs de corpo da requisição ou de credenciais.

A preparação gera segredos aleatórios por usuário e salva os acessos somente em arquivo local privado, com permissão `0600`: `/tmp/bb-demo-acessos.json`. Esse arquivo não está no repositório. Sua finalidade é permitir o acesso manual à DEMO; o banco contém apenas hashes. Reexecutar a preparação com o mesmo arquivo preserva os hashes. Arquivo com credenciais diferentes das existentes é recusado, sem trocar senhas silenciosamente.

## Usuários existentes e prefixos

O seed e os vínculos locais foram consultados antes de qualquer alteração. Nenhum usuário, papel ou alçada foi duplicado ou criado para o login.

| Perfil | Matrícula existente | Prefixos ativos preparados |
| --- | --- | --- |
| Maker Recife | `DEMO-maker` | `REC-DEMO` |
| Maker Paulista | `DEMO-maker-paulista` | `PAU-DEMO` |
| Maker Multi-Prefixo | `DEMO-maker-multi` | `REC-DEMO`, `PAU-DEMO` |
| Checker | `DEMO-checker` | `REC-DEMO`, `PAU-DEMO` |
| Alçada reduzida | `DEMO-limite-baixo` | `REC-DEMO` |

Maker Recife, Checker e alçada reduzida tinham vínculos históricos adicionais. A preparação DEMO desativou os vínculos fora da definição acima, preservando as linhas históricas, as contas, os nomes, as funções e as alçadas. O primeiro prefixo de cada perfil é o principal. O script usa o serviço existente de vínculos, incluindo sua revalidação cadastral.

Um único prefixo ativo é selecionado automaticamente. Para múltiplos, o principal inicia como ativo e o seletor permite somente prefixos autorizados. A seleção é persistida na sessão e reaparece ao atualizar a página. Uma troca inválida é recusada sem substituir o prefixo anterior. O cabeçalho acompanha a unidade ativa.

Preparação local:

```bash
cd backend
.venv/bin/alembic upgrade head
.venv/bin/python scripts/prepare_demo_auth.py --ambiente-demo --arquivo /tmp/bb-demo-acessos.json
```

É necessário que os usuários e prefixos do seed já existam. O script de autenticação não cria cadastros substitutos. Não é necessário reexecutá-lo para cada login ou reinício do servidor.

## Identidade, autorização e processamento

A API operacional exige sessão; não existe fallback público para a identidade declarada antiga. `get_contexto_operacional` obtém o usuário da sessão e resolve o prefixo autorizado, usando o ativo quando a requisição não informa outro prefixo autorizado. O frontend normal não envia `id_usuario` no upload ou processamento.

Upload e leitura continuam documento-first. `Documento.id_usuario_contexto` e `id_prefixo_contexto`, assim como a extração posterior, recebem a identidade resolvida pelo backend. Não foram alterados os providers, o cálculo ou a criação documental da ContaConsumo.

A autorização também ocorre no servidor:

- Identidade declarada diferente da sessão é recusada, em query ou corpo.
- Referências a prefixos externos são recusadas.
- Listas de prefixos, contas, documentos, extrações, dados, itens, cálculos, ordens e aprovações recebem filtro por vínculos autorizados; buscas diretas por ID externo retornam 404.
- A API de usuários apresenta somente o próprio usuário no acesso DEMO.
- Alterações cadastrais de usuários, alçadas, vínculos, regras e outros cadastros administrativos ficam indisponíveis ao login DEMO. Isso impede ampliar a própria autorização ou alterar a situação de uma ordem por CRUD para contornar aprovação.
- Mutations verificam Origin quando presente. Cookies SameSite e lista explícita de origens locais impedem chamadas de navegador de uma origem externa.

Criação de ordem e de aprovação recebem a identidade autenticada no backend; o frontend não precisa enviar o ID do autor/aprovador. A tela legada de aprovação também utiliza a identidade da sessão, sem escolha de outro aprovador.

As regras continuam sendo as existentes: criador não decide sobre a própria ordem; aprovação exige a alçada financeira aplicável. Nenhuma regra nova de papel exclusivo maker/checker foi criada.

## Testes e validação

Foram acrescentados onze testes backend em `test_auth_demo.py`, incluindo:

- Login válido/inválido; senha/código protegidos inclusive em erros.
- Cookie HttpOnly, persistência de sessão, logout e revogação.
- Expiração, usuário inativo e autenticação DEMO desabilitada.
- Prefixo único, múltiplos, principal, troca persistida e prefixo externo.
- Tentativa de forjar identidade ou editar privilégios.
- Maker não aprova própria ordem; checker aprova; alçada reduzida é recusada.
- Upload e leitura com usuário da sessão, usando provider simulado; isolamento por prefixo.
- Criação de ordem com autor da sessão e recusa de cálculo externo, inclusive para tipos JSON alternativos.
- Origin externo recusado e preparação sem duplicação de usuários ou troca dos hashes.

**Resultado final: 308 testes backend aprovados**, incluindo toda a suíte anterior e os onze testes novos. A suíte de regressão anterior conserva seus cenários de domínio. A fixture legada ignora explicitamente a nova fronteira HTTP e mantém seu contexto antigo apenas em testes; os testes de autenticação removem esses overrides e exercitam a autenticação real. O patch do teste da dependência de banco foi atualizado para o módulo onde essa dependência passou a residir.

**Build e lint frontend passaram.** Comandos executados: `npm run build`, `npm run lint`, `npm test`. Os dois testes unitários anteriores permanecem aprovados. Os scripts Playwright usam instalação externa ao runtime da aplicação:

- `review/document-flow.cjs`: sessão simulada, prefixo único/múltiplos, resumo e edição canônica.
- `review/auth-demo.cjs`: backend real, acesso direto sem sessão, login Maker Recife, prefixo único, atualização da página, logout, login Multi-Prefixo, troca/persistência de unidade e upload autenticado.
- `review/browser-review.cjs`: revisão visual anterior adaptada ao login e ao contrato documental atual.

Os três scripts de navegador passaram; a revisão visual anterior gerou nove capturas em `/tmp/bb-review-auth`, sem alterar os screenshots versionados. A validação real de navegador usou o PDF indicado somente para upload. O documento de conferência 28 foi verificado no banco com usuário `DEMO-maker-multi`, prefixo `PAU-DEMO` e `id_conta` nulo. A requisição de leitura foi interceptada e abortada antes do backend. Nenhuma chamada Gemini/OpenAI foi executada nesta tarefa. O teste backend com provider simulado confirmou os IDs de usuário e prefixo recebidos pelo processamento.

## Limitações antes de deploy

Esta é uma autenticação DEMO local. O código estático do campo “2º fator” é um segredo DEMO protegido por hash, não MFA. Não há recuperação de senha, cadastro público ou autenticação institucional.

Antes de expor uma DEMO na internet: usar HTTPS e `DEMO_COOKIE_SECURE=true`, definir origens exatas, definir política de provisionamento/rotação e guarda dos segredos, acrescentar limitação de tentativas e monitoramento, revisar autorização administrativa e política de sessões. `DEMO_AUTH_ENABLED` deve continuar desabilitado fora de ambiente DEMO explícito. Cookies locais sem Secure servem apenas ao HTTP local desta validação.

O cadastro inicial geral continua sendo uma operação de preparação/manutenção local; o login DEMO não ganha permissões administrativas para executar o seed pela API. A validade da sessão é conferida no backend a cada requisição; a interface detecta sua expiração na próxima chamada.

Sem commit, push ou deploy. As alterações anteriores do fluxo documental e de `scripts/start_frontend.sh` foram preservadas.
