# BB Contas IA — MVP web

React, Vite, TypeScript, React Router e Lucide React. Cliente HTTP com fetch nativo.
Backend FastAPI e PostgreSQL separados; fórmulas e regras permanecem no backend.

## Iniciar

Backend (ambiente e banco já configurados):

```bash
cd backend
source .venv/bin/activate
.venv/bin/alembic upgrade head
# Configure DEMO_MODE=true no backend/.env apenas para a DEMO local.
.venv/bin/python scripts/prepare_demo_auth.py --ambiente-demo --arquivo /tmp/bb-demo-acessos.json
uvicorn app.main:app --reload
```

Frontend, em outro terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Acesse http://127.0.0.1:5173. Alternativa: `bash scripts/start_frontend.sh` na raiz.
`VITE_API_URL` é obrigatória e define exclusivamente a origem da API; copie o exemplo local antes de iniciar.
O cliente acrescenta `/api/v1`. CORS já permite localhost:5173 e 127.0.0.1:5173,
sem wildcard e com cookies autenticados. Use as matrículas DEMO e os segredos do arquivo privado gerado.

## Rotas e jornada

- `/`: login DEMO com matrícula, senha e código local de demonstração.
- `/pagamentos`: upload, leitura, resumo, ajuste manual, validação e conclusão.
- `/faturas`: busca, filtros, tabela e ação para envio.
- `/relatorios`: placeholder.

A sessão é persistida no backend e em cookie HttpOnly por oito horas. Atualizar a página preserva o login; “Sair” revoga a sessão. Rotas internas exigem sessão válida.
Hospedagem futura deve encaminhar rotas para index.html (BrowserRouter).

## Contratos reutilizados

Login e sessão: POST `auth/login`, GET `auth/sessao`, PATCH `auth/prefixo`, POST `auth/logout`.
A sessão fornece identidade, prefixos autorizados e unidade ativa. Um prefixo é automático;
múltiplos aparecem em seletor autorizado antes do processamento.
POST `documentos/upload` (multipart, `file`) e POST `documentos/{id}/processar-inteligente`
iniciam a jornada sem ContaConsumo prévia. O usuário vem do cookie, não de um ID manual.
PATCH `dados_extraidos/{id}/validacao`, PATCH `itens_extraidos/{id}/validacao` e
POST `contas_consumo/{id}/calcular` preservam a revisão humana e as regras do backend.
O valor original é preservado; competência é canônica AAAA-MM e apresentada MM/AAAA.

## Assets e componentes

`public/assets/`: bb-logo.png, bb-symbol.png, login-hero.png,
dashboard-banner.png, avatar-demo.png e invoice-placeholder.png.
São os seis assets existentes, renomeados após inspeção visual.
O placeholder é ilustrativo, não representa dados extraídos.

`components/payment/`: AppShell, Sidebar, Topbar, PaymentStepper,
ProcessingState, UploadArea, InvoiceSummary, DocumentPreview, EditInvoiceModal,
CalculationSummary, ValidationSummary e ConfirmationCard.

## Limitações

- A criação de ContaConsumo exige leitura elegível e correspondência cadastral; evidência insuficiente permanece em revisão.
- Extração síncrona sem progresso intermediário: indicador indeterminado, sem percentual inventado.
- O prefixo vem da sessão; concessionária e unidade exibidas vêm do documento, com validação cadastral separada.
- O cálculo exige campos/componentes validados e perfil/regra vigentes no cadastro.
- A edição salva valores validados via API; as requisições não são uma transação única.
  Em falhas parciais, valores já salvos permanecem e a operação pode ser repetida.
- Conclusão registra a conclusão visual da revisão e mostra o cálculo persistido.
  Não cria ordem, aprovação ou encaminhamento bancário. A data exibida é a do cálculo.
- Autenticação exclusivamente DEMO local; sem SSO, MFA institucional ou pagamento bancário.
- Relatórios permanecem como placeholder. Páginas técnicas antigas não são rotas do MVP.

## Verificação

```bash
npm run build
npm run lint
npm run type-check
npm test
git diff --check
```

Capturas em `review/screenshots/01-login.png` até `09-relatorios.png` (1366×768).
`review/browser-review.cjs` usa Playwright externo ao runtime para revisão visual
com respostas de API simuladas; não instala dependências na aplicação.
Execute com `PLAYWRIGHT_MODULE=/caminho/node_modules/playwright node review/browser-review.cjs`.
Isso verifica a UI e os contratos consumidos; não comprova integração com o banco real.

Arquitetura, perfis, credenciais locais e limites antes de deploy: [autenticação DEMO](../RELATORIO_AUTENTICACAO_DEMO.md).

Preparação de homologação, variáveis, storage e seleção de hosting: [DEPLOY.md](../DEPLOY.md). Nenhuma publicação foi executada.

Documentos: `DOCUMENT_STORAGE_PROVIDER=local` no desenvolvimento ou `r2` para storage privado externo. Novos uploads R2 permitem backend efêmero; a configuração e a preservação do legado estão em [DEPLOY.md](../DEPLOY.md).
