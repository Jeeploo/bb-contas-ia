# BB Contas IA — MVP web

React, Vite, TypeScript, React Router e Lucide React. Cliente HTTP com fetch nativo.
Backend FastAPI e PostgreSQL separados; fórmulas e regras permanecem no backend.

## Iniciar

Backend (ambiente e banco já configurados):

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Frontend, em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Acesse http://127.0.0.1:5173. Alternativa: `bash scripts/start_frontend.sh` na raiz.
`VITE_API_URL` permite configurar a raiz da API (padrão http://127.0.0.1:8000).
O cliente acrescenta `/api/v1`. CORS já permite localhost:5173 e 127.0.0.1:5173,
sem wildcard. Nenhuma alteração no backend nesta entrega.

## Rotas e jornada

- `/`: acesso demonstrativo, sem envio ou persistência dos campos.
- `/pagamentos`: upload, leitura, resumo, ajuste manual, validação e conclusão.
- `/pagamentos?conta=ID`: upload vinculado à conta escolhida em Faturas.
- `/faturas`: busca, filtros, tabela e ação para envio.
- `/relatorios`: placeholder.

O acesso é mantido apenas em memória. Recarregar exige entrar novamente.
Hospedagem futura deve encaminhar rotas para index.html (BrowserRouter).

## Contratos reutilizados

GET `contas_consumo`, `prefixos`, `concessionarias` com paginação.
POST `contas_consumo/{id}/documentos/upload` (multipart, `file`),
POST `documentos/{id}/processar`, PATCH `dados_extraidos/{id}/validacao`,
PATCH `itens_extraidos/{id}/validacao`, POST `contas_consumo/{id}/calcular`.
O frontend envia somente valores validados, nunca fórmula ou alteração do original.

## Assets e componentes

`frontend/public/assets/`: bb-logo.png, bb-symbol.png, login-hero.png,
dashboard-banner.png, avatar-demo.png e invoice-placeholder.png.
São os seis assets existentes, renomeados após inspeção visual.
O placeholder é ilustrativo, não representa dados extraídos.

`frontend/src/components/payment/`: AppShell, Sidebar, Topbar, PaymentStepper,
ProcessingState, UploadArea, InvoiceSummary, DocumentPreview, EditInvoiceModal,
CalculationSummary, ValidationSummary e ConfirmationCard.

## Limitações

- Upload exige conta previamente cadastrada; seleção secundária no card.
- Imagens podem ser selecionadas, mas a leitura atual exige PDF; a interface orienta a troca.
- Extração síncrona sem progresso intermediário: indicador indeterminado, sem percentual inventado.
- Agência e unidade consumidora extraídas não são retornadas pelo extrator atual;
  campos ausentes são omitidos. Prefixo e concessionária vêm do cadastro vinculado.
- O cálculo exige campos/componentes validados e perfil/regra vigentes no cadastro.
- A edição salva valores validados via API; as requisições não são uma transação única.
  Em falhas parciais, valores já salvos permanecem e a operação pode ser repetida.
- Conclusão registra a conclusão visual da revisão e mostra o cálculo persistido.
  Não cria ordem, aprovação ou encaminhamento bancário. A data exibida é a do cálculo.
- Sem autenticação real, novo OCR, integração de modelos ou pagamento bancário.
- Relatórios permanecem como placeholder. Páginas técnicas antigas não são rotas do MVP.

## Verificação

```bash
npm run build
npm run lint
npm run type-check
git diff --check
```

Capturas em `frontend/review/screenshots/01-login.png` até `09-relatorios.png` (1366×768).
`frontend/review/browser-review.cjs` usa Playwright externo ao runtime para revisão visual
com respostas de API simuladas; não instala dependências na aplicação.
Execute com `PLAYWRIGHT_MODULE=/caminho/node_modules/playwright node review/browser-review.cjs`.
Isso verifica a UI e os contratos consumidos; não comprova integração com o banco real.
