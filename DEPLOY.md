# Preparação de deploy — demonstração/homologação

**Estado: preparado para revisão, não publicado.** Nenhuma conta, serviço, domínio ou recurso externo foi criado. Nenhum commit/push foi feito. Regras financeiras, autenticação DEMO e providers foram preservados. Todos os comandos abaixo são procedimentos para uma publicação futura autorizada; seed e migrations não fazem parte do start automático.

## 1. Arquitetura

```text
Navegador autorizado
  → frontend React/Vite estático, HTTPS
  → backend FastAPI, HTTPS, cookie HttpOnly
      → PostgreSQL gerenciado por DATABASE_URL (TLS)
      → Gemini OU OpenAI por secrets do backend
      → Cloudflare R2 privado (S3) para documentos/PDFs
```

Recomenda-se `app.exemplo.com` e `api.exemplo.com`, sob o mesmo domínio registrável e ambos HTTPS. Uma instância e um worker de backend nesta etapa porque o rate limit é local ao processo. Com R2, documentos não exigem volume do backend. Não usar funções serverless para o backend atual.

**Storage externo implementado:** `DOCUMENT_STORAGE_PROVIDER=r2` permite filesystem efêmero para novos documentos. O backend acessa objetos privados por bytes, sem URL pública. `local` continua sendo o padrão de desenvolvimento. Nenhum bucket foi criado ou acessado nesta preparação. Arquivos locais antigos não são enviados automaticamente ao R2.

## 2. Frontend

Raiz do serviço: `frontend/`. Node compatível com Vite 6; utilizar Node 22 LTS. Instalar com lockfile no pipeline:

```bash
cd frontend
npm ci
VITE_API_URL=https://api.exemplo.com npm run build
```

`npm install` também foi conferido localmente, com cache offline. Publicar somente o diretório `frontend/dist` gerado. Ele está ignorado no Git; não foi adotada estratégia de versionar builds.

`VITE_API_URL` é a **única** origem usada pelo cliente HTTP. É obrigatória e deve ser uma origem HTTP/HTTPS sem `/api/v1`, credenciais ou query. O cliente acrescenta `/api/v1`; não há fallback para hostname, localhost ou porta 8000. Como é configuração de build, mudar a URL exige reconstruir o frontend. Não colocar API keys ou outros secrets em `VITE_*`: esses valores são públicos no bundle.

Para desenvolvimento:

```bash
cp frontend/.env.example frontend/.env.local
cd frontend
npm install
npm run dev
```

Abrir o frontend e a API com o mesmo hostname local: ambos `127.0.0.1`, ou ambos `localhost`, para cookies SameSite funcionarem. O exemplo aponta para `127.0.0.1`.

BrowserRouter exige fallback de rotas internas para `index.html`. `public/_redirects` prepara esse comportamento para Cloudflare Pages/Netlify. No Render Static Site, configurar rewrite `/*` → `/index.html` (200). Em Vercel, configurar o rewrite equivalente se escolhida. Não reescrever requisições da API para HTML.

## 3. Backend

Raiz do serviço: `backend/`. Python 3.12 (mesma versão de validação local). Build:

```bash
python -m pip install -r requirements.txt
```

Start recomendado:

```bash
sh scripts/start.sh
```

O script usa a virtualenv local quando disponível; no hosting usa o Python do runtime. Executa `python -m app.start`, equivalente a:

```bash
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --no-access-log \
  --proxy-headers --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
```

Sem `PORT`, o padrão é 8000. O start não executa seed, migrations nem IA. Não usar `--reload` ou múltiplos workers em homologação nesta configuração. Configurações externas inseguras são recusadas antes de iniciar: origem não HTTPS, cookie sem Secure, banco local/não PostgreSQL e storage inválido. Para `r2`, exige configuração R2 completa; para `local` externo, exige volume persistente e caminho absoluto.

`FORWARDED_ALLOW_IPS` aceita apenas os proxies conhecidos. Não ler manualmente `X-Forwarded-For` fornecido pelo cliente. Confiar em `*` só seria justificável se o ingresso privado do host garantir que **toda** conexão venha exclusivamente de seu proxy; isso precisa ser confirmado antes da publicação. Sem configuração correta, o rate limit pode agregar visitantes no IP do proxy.

Gemini/OpenAI leem PDF/imagem diretamente. O fluxo OCR legado continua disponível; se for utilizado, o host também precisará de Tesseract e dos idiomas já exigidos pelo backend. Não foi removido nem instalado OCR no host nesta preparação.

## 4. PostgreSQL

Utilizar banco separado de demonstração, nunca o banco de trabalho local ou um banco real institucional. `DATABASE_URL` vem do secret manager do host. URLs `postgres://`, `postgresql://` e `postgresql+psycopg://` são aceitas e normalizadas para o driver psycopg já instalado. Query parameters do provedor, como `sslmode=require` ou validação de certificado, são preservados.

Em conexão externa pública, habilitar TLS conforme instrução do provedor. Não copiar a URL para Git, prints, tickets, histórico de comandos com segredo literal ou variáveis VITE. O engine usa `pool_pre_ping` para recuperar conexões encerradas pelo banco e `hide_parameters` para não imprimir valores SQL.

Preferir a conexão direta do PostgreSQL para migrations. Se utilizar uma URL com pooler no runtime, conferir compatibilidade do pooler com transações e migrations; usar a conexão direta na etapa administrativa. Não foi criado um banco externo nesta tarefa. A compatibilidade foi verificada por configuração/normalização, suíte e migrations locais; não há teste de conectividade com um provedor ainda inexistente.

## 5. Migrations

Executar uma vez, sob controle do operador e com o mesmo código/variáveis da versão a publicar, antes de servir a nova aplicação:

```bash
cd backend
alembic upgrade head
alembic current
```

O histórico já inclui documentos sem conta prévia e as tabelas de credenciais/sessões DEMO. A migration aditiva `e61d4b902f30` acrescenta `documentos.storage_provider` e `storage_key`. Registros existentes recebem `local` e uma cópia exata de `caminho_arquivo`; nenhum arquivo é movido, apagado ou enviado a outro serviço. `caminho_arquivo` continua como referência compatível, inclusive nos contratos já consumidos pelo frontend. A metadata de storage é interna ao backend.

Não executar migrations concorrentes por worker/réplica. Fazer backup antes de alterações de schema. No Render, usar pre-deploy quando disponível ou um job administrativo controlado; não é necessário montar o volume de PDFs para migrar o banco. O start continua independente.

## 6. Variáveis

Os exemplos oficiais são `backend/.env.example` e `frontend/.env.example`, sem segredo real. Variáveis do host têm precedência sobre `.env`.

| Variável backend | Uso / valor de referência |
| --- | --- |
| `APP_ENV` | `development`, `test`, `homologation`/`staging` ou `production`. Fora de dev/test, aplica verificações externas. |
| `DEMO_MODE` | `true` somente no ambiente de demonstração; habilita login/credenciais DEMO e os comandos de preparação. |
| `DATABASE_URL` | Secret de PostgreSQL externo, com TLS conforme provedor. |
| `FRONTEND_ORIGIN` | Uma origem HTTPS exata, sem barra final, lista ou wildcard. |
| `SESSION_COOKIE_SECURE` | `false` no HTTP local; `true` obrigatório em ambiente externo. |
| `SESSION_COOKIE_SAMESITE` | `strict`, `lax` ou `none`; `none` exige Secure. |
| `SESSION_TTL` | Validade absoluta em segundos; padrão `28800` (8 h). |
| `LOGIN_MAX_ATTEMPTS` | Máximo de falhas por janela antes do bloqueio; padrão `5`. |
| `LOGIN_WINDOW_SECONDS` | Janela de contagem; padrão `300`. |
| `LOGIN_BLOCK_SECONDS` | Duração do bloqueio; padrão `300`. |
| `PORT` | Porta fornecida pelo host; padrão local `8000`. |
| `FORWARDED_ALLOW_IPS` | Proxies confiáveis do ingresso; padrão `127.0.0.1`. |
| `DOCUMENT_STORAGE_PROVIDER` | `local` (padrão) ou `r2`. A seleção vale para novos uploads; documentos existentes usam seu próprio provider. |
| `DOCUMENT_STORAGE_PATH` | Diretório local de desenvolvimento ou volume se optar por `local` no host. Não é usado pelos objetos R2. |
| `DOCUMENT_STORAGE_PERSISTENT` | Apenas para `local` externo: `true` exige planejar/montar volume real. Com `r2`, pode permanecer `false`. |
| `R2_ENDPOINT` | Origem HTTPS da API S3 da conta R2, ex. `https://ACCOUNT_ID.r2.cloudflarestorage.com`; não usar URL pública do objeto. |
| `R2_BUCKET` | Bucket privado dedicado aos documentos da DEMO. |
| `R2_ACCESS_KEY_ID` | Secret S3/R2 do backend, limitado ao bucket. |
| `R2_SECRET_ACCESS_KEY` | Secret S3/R2; nunca em frontend, Git ou logs. |
| `R2_REGION` | `auto` por padrão. |
| `DOCUMENT_MAX_SIZE_BYTES` | Tamanho máximo de upload; padrão `10485760`. |
| `MAX_OCR_PAGES` | Limite do fluxo OCR; padrão `10`. |
| `UF_MVP` | Escopo regional existente; padrão `PE`; não alterar para contornar validação. |
| `DOCUMENT_AI_PROVIDER` | `gemini` ou `openai`; sem fallback automático. |
| `GEMINI_API_KEY` | Secret apenas no backend quando Gemini for selecionado. |
| `GEMINI_DOCUMENT_MODEL` | Modelo explícito permitido ao projeto. Exemplo atual: `gemini-2.5-flash-lite`; conferir disponibilidade antes de publicar. |
| `GEMINI_DOCUMENT_TIMEOUT` / `GEMINI_DOCUMENT_MAX_OUTPUT_TOKENS` | Limites de leitura; padrões `90` / `6000`. |
| `OPENAI_API_KEY` / `OPENAI_DOCUMENT_MODEL` | Secret/modelo explícito se OpenAI for selecionado. |
| `OPENAI_DOCUMENT_TIMEOUT` / `OPENAI_DOCUMENT_MAX_OUTPUT_TOKENS` | Limites de leitura; padrões `90` / `6000`. |

Frontend: somente `VITE_API_URL`, definido no build. Os nomes antigos `DEMO_AUTH_ENABLED` e `DEMO_COOKIE_SECURE` são aceitos como compatibilidade local quando os canônicos estão ausentes; não usá-los em um novo ambiente. `DEMO_ALLOWED_ORIGINS` deixou de controlar a origem; migrar para `FRONTEND_ORIGIN`. `DOCUMENT_STORAGE_BACKEND=filesystem` continua aceito somente como compatibilidade da configuração antiga; a seleção atual é `DOCUMENT_STORAGE_PROVIDER`.

Exemplo externo sem segredos (a URL e chaves reais devem vir dos secrets):

```dotenv
APP_ENV=homologation
DEMO_MODE=true
FRONTEND_ORIGIN=https://app.exemplo.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=strict
SESSION_TTL=28800
LOGIN_MAX_ATTEMPTS=5
LOGIN_WINDOW_SECONDS=300
LOGIN_BLOCK_SECONDS=300
DOCUMENT_STORAGE_PROVIDER=r2
DOCUMENT_STORAGE_PERSISTENT=false
R2_ENDPOINT=https://ACCOUNT_ID.r2.cloudflarestorage.com
R2_BUCKET=bb-contas-demo
R2_REGION=auto
# R2_ACCESS_KEY_ID e R2_SECRET_ACCESS_KEY fornecidos como secrets do backend.
DOCUMENT_AI_PROVIDER=gemini
```

## 7. Cookies e CORS

Em desenvolvimento, CORS permite as origens locais `http://127.0.0.1:5173` e `http://localhost:5173`; pode acrescentar a origem exata configurada. Em homologação/produção, permite **somente** `FRONTEND_ORIGIN`, com credenciais; não há wildcard nem liberação automática de previews/domínios locais. A mesma lista valida Origin nas mutações autenticadas e no login.

| Cenário | Secure | SameSite | Observação |
| --- | --- | --- | --- |
| HTTP local, mesmo hostname | `false` | `strict` | Portas diferentes são origens distintas; CORS continua necessário. |
| `https://app.exemplo.com` → `https://api.exemplo.com` | `true` | `strict` ou `lax` | Mesmo site registrável/esquema, apesar de serem origens distintas. Opção preferida. |
| `https://projeto.pages.dev` → `https://api.onrender.com` | `true` | `none` | Sites diferentes. O navegador pode bloquear cookies de terceiros mesmo com essa configuração. |

`SameSite=None` exige `Secure=true`; isso é validado pelo backend. O cookie continua HttpOnly e host-only, sem ampliar Domain para todo o domínio. O fetch já envia `credentials: include`. CORS sozinho não torna um cookie cross-site utilizável. Para evitar bloqueios de terceiros, escolher subdomínios do mesmo domínio registrável ou, futuramente, um proxy da API na mesma origem. Não foi implementado proxy remoto nesta tarefa. Ver [Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie) e [CORS com credenciais](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS).

## 8. Base DEMO manual

A preparação foi corrigida para funcionar **antes de iniciar o servidor**, diretamente por `DATABASE_URL`, usando os mesmos services/validações do seed. Não depende da antiga API administrativa pública. Nenhum bypass de autenticação foi criado na aplicação.

Em ambiente administrativo de confiança, com variáveis do banco alvo e `DEMO_MODE=true`:

```bash
cd backend
alembic upgrade head
python scripts/seed_demo.py --ambiente-demo
python scripts/prepare_demo_auth.py --ambiente-demo --arquivo /CAMINHO_PRIVADO/bb-demo-acessos.json
```

O diretório privado precisa existir e ser acessível ao operador. O arquivo é criado com permissão `0600`; copiar seus acessos para um cofre/gestão segura de secrets e distribuir individualmente aos testadores autorizados. Não colocar o arquivo em `frontend/public`, `dist`, Git ou logs. Não depender de `/tmp` do host para sua guarda após a preparação. O comando gera os valores previsíveis 1/1 a 5/5. Reexecuções preservam hashes correspondentes; credenciais anteriores diferentes são substituídas, revogando as sessões dos usuários afetados.

O seed mantém sua idempotência e dados fictícios. `--cenario` permite outro ensaio controlado. A preparação de autenticação reutiliza os cinco usuários existentes sem duplicá-los ou mudar vínculos de prefixos e regras de alçada. Os vínculos precisam estar previamente preparados e conferidos no banco DEMO. Não executar seed em produção institucional. Nenhum desses passos roda em build/start/healthcheck.

## 9. Autenticação DEMO e limitação de login

Mantidos login, sessão HttpOnly no PostgreSQL, revogação por logout, seleção autorizada de prefixo, identidade derivada da sessão, bloqueio de autoaprovação e alçada existente. Os campos senha e código DEMO permanecem protegidos com scrypt e salts individuais. Não é SSO nem MFA institucional.

O limiter conta falhas por IP e por matrícula normalizada, mantendo apenas hashes e contadores em memória. Depois de `LOGIN_MAX_ATTEMPTS` falhas dentro da janela, novas tentativas recebem 429 com mensagem genérica e `Retry-After`, inclusive se a matrícula não existir. Não recebe nem armazena senha, código, cookie ou PDF. Expira automaticamente e tem limite de memória com recusa temporária quando saturado.

Limitação assumida: um processo/instância; reiniciar limpa o limiter. Sessões não se perdem porque ficam no PostgreSQL. Para múltiplos workers/réplicas, será necessário um limiter compartilhado ou proteção equivalente no ingresso; isso não foi implementado. Identificação do IP depende da configuração correta dos proxies confiáveis. Não usar headers arbitrários do visitante para escapar do limite.

## 10. Gemini/OpenAI e secrets

Configurar apenas a chave do provider selecionado, o modelo explícito e limites. Conferir acesso, quota, orçamento, timeout do host/proxy e política de uso do projeto antes de permitir leituras. Não colocar keys no frontend, código, seed ou arquivos publicados.

O provider é escolhido pelo backend. OpenAI foi preservado, assim como Gemini, sem fallback nem retries automáticos adicionais. Os scripts de inicialização/seed/migration/health não fazem chamadas a nenhum provider. Esta preparação não executou leituras reais.

Logs externos omitem a mensagem/corpo de erro do provider OpenAI; ficam códigos técnicos internos e status. Erros não tratados externos são devolvidos como erro genérico e registrados apenas por tipo e método, sem repr, query, SQL/valores ou conteúdo do documento. O start desativa access logs crus do Uvicorn, que poderiam registrar segredos colocados por terceiros em URLs. Não habilitar debug HTTP/SDK ou logging de corpo/headers no host.

## 11. Storage local e Cloudflare R2

`DocumentStorage` define `save`, `read` e `delete`. `LocalDocumentStorage` preserva o comportamento anterior; `R2DocumentStorage` usa boto3/botocore pela API compatível com S3. Os services selecionam o storage pela metadata do documento, sem conhecer sua localização física. Não há fallback silencioso para disco quando R2 falha.

Fluxo: validar tamanho, extensão/MIME e conteúdo → salvar por `DocumentStorage.save` → persistir `storage_provider` e `storage_key`. A chave R2 tem formato `documentos/<uuid>/<sha256>.<extensão>`. Não contém nome do arquivo original, unidade consumidora, código de barras ou outro dado pessoal. O banco armazena a chave lógica, sem caminho absoluto do host ou URL pública.

Leitura: `DocumentStorage.read` devolve bytes diretamente ao Gemini/OpenAI. O stream S3 é lido com limite de tamanho e fechado; o arquivo não é baixado para um diretório temporário. Hash, idempotência e reprocessamento usam os bytes como antes. Mesmo que o default seja alterado depois, um documento `r2` continua sendo lido no R2 e um documento `local` continua sendo lido no diretório local. Para manter acesso a documentos R2 antigos, preservar bucket/endpoint e as permissões de leitura; trocar de bucket não migra os objetos.

Configuração local (padrão):

```dotenv
DOCUMENT_STORAGE_PROVIDER=local
DOCUMENT_STORAGE_PATH=./storage/documentos
```

Configuração externa desejada: `DOCUMENT_STORAGE_PROVIDER=r2`, as cinco variáveis R2 da tabela e secrets válidos no backend. Isso remove a exigência de volume persistente para **novos uploads R2** e permite Render Free inicialmente. O banco continua externo e persistente.

### Bucket e permissões — procedimento futuro, não executado

Quando a criação de infraestrutura for autorizada, criar um bucket privado dedicado e credenciais S3 limitadas a esse bucket. Não conceder administração da conta/criação de buckets. As operações necessárias ao código são `PutObject`, `GetObject` e `DeleteObject`: exclusão já é utilizada na compensação quando o upload funciona e a transação no banco falha. No R2, escolher a capacidade de objetos de leitura/escrita restrita ao bucket, conferindo a política de menor privilégio disponível. O SDK não lista/cria buckets nem altera ACL/política.

Manter acesso público (`r2.dev` e domínio público de bucket) desabilitado. Não gerar URL pública permanente ou presigned URL no fluxo atual. CORS do bucket não é necessário para o navegador: ele fala com o backend autenticado, e somente o backend fala com R2. Referências oficiais: [boto3 no R2](https://developers.cloudflare.com/r2/examples/aws/boto3/), [credenciais](https://developers.cloudflare.com/r2/api/tokens/) e [acesso público](https://developers.cloudflare.com/r2/buckets/public-buckets/).

O cliente usa credenciais explícitas, SigV4, região `auto` e timeout; não depende da cadeia de credenciais AWS/metadata de VM. Falhas do SDK são traduzidas para erros sanitizados, sem access key, secret, request, headers ou PDF. Objeto ausente retorna erro de arquivo indisponível; falha técnica retorna 503. Não habilitar DEBUG de boto3/botocore em homologação.

### Legado e consistência

A migration preserva referências locais e não converte arquivos. Para levar a base local atual para um backend efêmero **incluindo seus PDFs antigos**, será necessário planejar uma importação controlada ao R2 ou manter acesso ao storage local original. Essa importação não faz parte desta tarefa e não foi executada. Publicar a base DEMO sintética e usar R2 para novas faturas não exige copiar PDFs locais.

PostgreSQL e R2 não têm uma transação distribuída. O código tenta apagar o objeto novo se a persistência no banco falhar; se essa limpeza falhar, mantém o erro original e emite somente um aviso técnico. Uma falha ambígua de rede após escrita também pode deixar objeto órfão. Planejar reconciliação, retenção e backup de objetos/referências antes de uso prolongado; não configurar lifecycle que apague documentos ainda referenciados. Nenhum job destrutivo foi criado.

A prévia do frontend continua usando o `File` selecionado no navegador. Não foi criado download público ou endpoint novo de consulta de PDF; depois de recarregar, a interface não recupera a prévia automaticamente. Não houve alteração visual.

## 12. Healthcheck

`GET /health` é público e não exige sessão. Executa somente `SELECT 1`, sem provider ou arquivos.

- Banco disponível: HTTP 200, `{"status":"ok","database":"connected"}`.
- Banco indisponível: HTTP 503, `{"status":"ok","database":"error"}`.

`status` indica aplicação respondendo; `database` indica prontidão do banco. Não inclui URL, usuário, senha, cookie, host, conteúdo SQL ou exceção. Configurar o host para verificar `/health`, com timeout compatível com o cold start do banco. Não usar endpoint de processamento como probe.

## 13. Checklist pós-deploy — executar somente após autorização futura

- [ ] Confirmar URLs HTTPS, secrets, origem exata e flags de ambiente.
- [ ] Confirmar migrations no head e `/health` 200.
- [ ] Confirmar que uma origem externa/local não autorizada não recebe CORS.
- [ ] Confirmar cookie HttpOnly/Secure/SameSite no navegador real dos testadores; testar também restrição a cookies de terceiros se houver sites distintos.
- [ ] Login inválido e matrícula inexistente devem ter a mesma resposta genérica; conferir 429 e Retry-After após o limite e recuperação após bloqueio.
- [ ] Testar Maker Recife, prefixo único, reload, logout e bloqueio de rota interna sem sessão.
- [ ] Testar Multi-Prefixo limitado aos autorizados e persistência da unidade ativa.
- [ ] Confirmar identidade da sessão no upload/processamento, sem aceitar ID arbitrário.
- [ ] Confirmar autoaprovação bloqueada, checker autorizado e alçada reduzida recusada, usando somente dados de teste.
- [ ] Conferir R2 privado e credenciais restritas; subir arquivo de teste, reiniciar o backend e verificar leitura dos mesmos bytes/chave. Não repetir IA para testar storage.
- [ ] Se importar base antiga, conferir que documentos `local` não ficaram sem seus arquivos; não presumir migração automática ao R2.
- [ ] Conferir restore/backup do PostgreSQL e dos documentos como conjunto.
- [ ] Uma leitura IA real somente se necessária para integração; não repetir automaticamente.
- [ ] Conferir logs, quotas/orçamento do provider e ausência de segredos/documentos.

## 14. Rollback básico

Guardar referência da versão aprovada, configuração não secreta e backup antes de publicar. Para regressão de frontend/backend, voltar ao artefato anterior compatível e revalidar login/health, sem apagar banco, bucket ou arquivos locais legados. Evitar executar seed como mecanismo de rollback.

Se schema mudou, preferir versão anterior compatível com a migration aplicada. Não executar `alembic downgrade` automaticamente: documentos sem conta e histórico podem tornar o downgrade destrutivo. O downgrade da migration de storage é bloqueado se existirem documentos R2, para impedir que uma versão antiga os interprete como arquivos locais. Restaurar backup somente após avaliação/autorização, coordenando banco e objetos/documentos e aceitando a perda de alterações posteriores ao backup. Revogar/rotacionar sessões/segredos se o motivo do rollback envolver exposição. Preservar logs técnicos sem conteúdo sensível.

## 15. Hospedagem avaliada e recomendação

Consulta de documentação oficial em **01/11/2026**. Valores em USD, sujeitos a alteração, uso, impostos, domínio e políticas dos provedores. São estimativas para seleção, não orçamento fechado. Todos oferecem fluxos Git/GitHub e TLS gerenciado conforme o tipo de serviço; permissões de equipe/repositório devem ser conferidas antes de escolher um plano.

| Serviço | Adequação à aplicação |
| --- | --- |
| Render | FastAPI nativo e painel simples. Render Free atende inicialmente porque R2 preserva os documentos fora do backend. Considerar cold start, quotas e reinícios; o plano gratuito não oferece disco persistente. PostgreSQL gratuito expira em 30 dias, por isso não é o banco recomendado para histórico durável. [Preços](https://render.com/pricing), [limites gratuitos](https://render.com/docs/free), [FastAPI](https://render.com/docs/deploy-fastapi). |
| Railway | Backend com secrets e documentos no R2; volume não é necessário nessa configuração. Hobby com mínimo anunciado de US$5/mês, mais consumo excedente. Pode ser alternativa de baixo custo; não assumir que o crédito gratuito cobre a operação contínua. Para PostgreSQL totalmente gerenciado, manter Neon ou outro serviço apropriado em vez de presumir administração completa de um container de banco. [Preços](https://railway.com/pricing), [volumes](https://docs.railway.com/volumes/reference). |
| Fly.io | VMs e volumes atendem o backend; exige mais decisões operacionais/CLI. Há trial limitado e cobrança por recursos; não tratar como hospedagem gratuita permanente. [Trial](https://docs.fly.io/about/free-trial), [preços](https://www.fly.io/docs/about/pricing/). |
| Vercel | Adequado ao frontend estático. O plano Hobby tem restrição de uso pessoal/não comercial; confirmar elegibilidade da homologação da equipe. Não é escolhido para o processo FastAPI e leitura síncrona atuais. [Hobby](https://vercel.com/docs/plans/hobby). |
| Netlify | Adequado ao frontend e rewrites SPA; Free anunciado com 300 créditos/mês. Conferir limites e colaboração antes de usar para testes frequentes. [Preços](https://www.netlify.com/pricing/). |
| Cloudflare Pages | Preferido para o frontend estático de baixo custo, com GitHub e domínios próprios. O plano Free documenta 500 builds/mês. Não hospeda este processo FastAPI com disco de PDFs. [Limites](https://developers.cloudflare.com/pages/platform/limits/). |
| Neon PostgreSQL | Banco PostgreSQL gerenciado com plano Free para pequenos ensaios; na consulta, 1 GB/projeto e 100 CU-h/mês/projeto. Considerar suspensão por inatividade, quota, restore e latência ao acordar. [Preços](https://neon.com/pricing), [conexão](https://neon.com/docs/connect/connect-from-any-app). |

**Arquitetura principal recomendada:** Cloudflare Pages (frontend) + Render Free inicialmente (backend efêmero) + Neon Free (PostgreSQL) + Cloudflare R2 privado (documentos) + Gemini por secrets. Manter `app` e `api` sob domínio próprio da equipe quando possível, para cookies previsíveis. Esta é a arquitetura de demonstração, sem promessa de SLA ou custo permanentemente zero; conferir quotas, condições e orçamento do R2/IA antes da publicação. [Render Free](https://render.com/docs/free), [preços R2](https://developers.cloudflare.com/r2/pricing/).

**Alternativa:** Cloudflare Pages + Railway para o backend + Neon + R2 + Gemini. Também dispensa volume no backend. Railway pode cobrar por uso; manter orçamento e a mesma política de cookies/domínio.

O filesystem efêmero deixa de bloquear novos documentos porque seus bytes ficam no R2. O Render Free pode dormir/reiniciar; aceitar cold start para a DEMO e manter o limiter em um único processo. Nenhuma infraestrutura foi criada/publicada.

## 16. Verificações desta preparação

Os testes de preparação anteriores cobrem configuração por ambiente, CORS/preflight, Secure/SameSite/TTL, bloqueio de login e expiração, IP atrás de proxy não confiável, memória limitada, PORT, readiness sem vazamento, logs externos, modo DEMO e seed offline idempotente sem rede. A suíte anterior foi preservada. O build foi testado com `VITE_API_URL=https://api.exemplo.com`; essa URL é somente exemplo, não um serviço criado.

Os testes de storage R2 usam cliente S3 e IA simulados, bloqueiam conexões de rede e cobrem salvamento/leitura, tamanho, erro sanitizado, chave/hash, idempotência, reprocessamento, seleção por documento, legado local, rollback e migration aditiva. Nenhuma chamada real R2, Gemini ou OpenAI foi executada nesta tarefa. **Resultado final:** 340 testes backend aprovados (322 anteriores + 18 novos), 3 testes frontend aprovados, lint/build aprovados e `git diff --check` sem erros. O build utilizou `VITE_API_URL=https://api.exemplo.com`. `pip check` não identificou dependências quebradas. A migration foi validada em SQLite isolado e aplicada somente no PostgreSQL local, sem acessar R2 ou mover arquivos. Não houve criação de bucket, conta externa, commit, push ou deploy.


O login consulta `/api/v1/auth/config` para exibir os cinco perfis somente com
`DEMO_MODE=true`; senha e 2º fator continuam separados. Mapeamento das credenciais:

| Perfil | Matrícula | Senha | 2º fator |
| --- | --- | --- | --- |
| Maker Recife | DEMO-maker | 1 | 1 |
| Maker Paulista | DEMO-maker-paulista | 2 | 2 |
| Maker Multi-Prefixo | DEMO-maker-multi | 3 | 3 |
| Checker | DEMO-checker | 4 | 4 |
| Alçada reduzida | DEMO-limite-baixo | 5 | 5 |

Com `DEMO_MODE=false`, a matrícula permanece como campo livre e o backend recusa
login/sessão DEMO (503). Autenticação institucional continua pendente. O script
exige tanto `DEMO_MODE=true` quanto `--ambiente-demo`; nada é provisionado
automaticamente no início da aplicação.
