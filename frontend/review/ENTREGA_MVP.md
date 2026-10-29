# Entrega web — 29/10/2026

## Estado analisado antes das alterações

O projeto tinha backend FastAPI/SQLAlchemy, PostgreSQL, processamento documental,
validação e cálculo contextual implementados. O frontend tinha páginas técnicas antigas
e uma jornada demonstrativa em alterações locais ainda não commitadas. Essas alterações
foram aproveitadas, sem restaurar ou descartar o trabalho do usuário. Não foram alterados
arquivos do backend; a modificação preexistente em backend/MVP_DEMO.md foi preservada.
O CORS já contém as duas origens Vite solicitadas, sem wildcard; não exigiu ajuste.

## Inventário visual e renomeação

Todos os arquivos encontrados em public/assets foram inspecionados visualmente:

| Arquivo anterior (prefixo comum: Imagem do ChatGPT 29 de out. de 2026, ) | Nome permanente | Uso |
| --- | --- | --- |
| 14_00_14-1.png | bb-logo.png | Logo horizontal no acesso |
| 14_00_15-2.png | bb-symbol.png | Símbolo na sidebar/acesso |
| 14_00_16-3.png | login-hero.png | Imagem institucional do acesso |
| 14_00_18-4.png | dashboard-banner.png | Banner do cabeçalho |
| 14_00_20-5.png | avatar-demo.png | Perfil demonstrativo |
| 14_00_22-6.png | invoice-placeholder.png | Fallback ilustrativo do documento |

Nenhum asset substituto foi gerado. Imagens de referência em Downloads foram inspecionadas.

## Arquivos e dependências

Removidos: todo frontend/src-tauri (Cargo.toml, Cargo.lock, build.rs,
capabilities/default.json, icons/icon.png, src/main.rs, tauri.conf.json e artefatos locais),
script local scripts/start_desktop.sh; dependência @tauri-apps/cli e script npm tauri.

Criados: README.md na raiz, scripts/start_frontend.sh,
components/payment/ValidationSummary.tsx e review/browser-review.cjs.

Arquivos locais preexistentes aproveitados e atualizados: components/payment/AppShell.tsx
(AppShell, Sidebar, Topbar), PaymentStepper.tsx (inclui ProcessingState), UploadArea.tsx,
InvoiceSummary.tsx (InvoiceSummary, DocumentPreview, EditInvoiceModal, CalculationSummary,
ConfirmationCard); pages/DemoAccess.tsx, PaymentJourney.tsx e InvoiceHistory.tsx.

Alterados: package.json, package-lock.json, vite.config.ts, .gitignore,
eslint.config.js, src/main.tsx (BrowserRouter), src/styles.css, README.md,
ETAPA_6A.md (marcado como registro histórico) e DEMO_ROTEIRO.md (inicialização web).
Páginas técnicas antigas permanecem fora das rotas. Cliente HTTP usa fetch nativo.

## Rotas e APIs

Rotas: /, /pagamentos, /pagamentos?conta=ID, /faturas e /relatorios.
APIs: GET contas_consumo, prefixos e concessionarias; POST upload da conta,
POST processamento do documento, PATCH validação dos dados e itens,
POST contas_consumo/{id}/calcular, sempre sob /api/v1.

## Validação

- npm install --offline --ignore-scripts: concluído; dependência Tauri removida.
- npm run build: aprovado.
- npm run lint: aprovado.
- npm run type-check: aprovado.
- git diff --check: aprovado.
- npm run dev: Vite iniciado em http://127.0.0.1:5173.
- Chromium/Playwright: percurso das nove telas, edição, seleção de imagem,
  navegação e ausência de overflow horizontal em 375, 768, 1366, 1440 e 1920 px.
- Nove screenshots atuais em 1366×768: 01-login, 02-upload, 03-processamento,
  04-resumo, 05-edicao, 06-validacao, 07-confirmacao, 08-faturas e 09-relatorios.
  Capturas antigas preexistentes foram preservadas; os nomes acima identificam a revisão atual.
- A revisão usa API simulada no navegador. Backend local não estava respondendo em 8000;
  não houve validação ponta a ponta com PostgreSQL, alteração de banco ou alegação de pagamento.
- Backend não foi alterado; suíte backend não executada nesta entrega.
- Sem commit nem push.

## Limitações documentadas

Upload requer conta cadastrada e PDF. Imagens são selecionáveis e recebem orientação clara.
Cálculo exige perfil/regra vigente e dados validados; ocorre exclusivamente no backend.
A API não fornece progresso intermediário, nome de agência ou unidade consumidora extraída
pelo extrator atual; não são inventados dados nem percentuais. O preview real usa URL local
da sessão; quando indisponível, há placeholder ilustrativo. Acesso demonstrativo em memória,
sem envio/persistência de credenciais. Conclusão encerra a revisão visual e mostra o cálculo
persistido; não cria ordem, aprovação ou encaminhamento bancário. Relatórios são placeholder.
