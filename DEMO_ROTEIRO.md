# Demonstração manual do MVP

Todos os cadastros `DEMO-*`, a concessionária, usuários, CNPJ com zeros e PDFs
são fictícios. Nenhum código possui validade para pagamento. Não há envio bancário.

## 1. Preparação antes da apresentação

Use o PostgreSQL local de desenvolvimento configurado em `backend/.env`, com
migrations aplicadas, ambiente `.venv`, dependências frontend/Rust e sessão gráfica.
Não exiba o `.env` nem credenciais. OCR requer Tesseract com `por` ou `eng` instalado.
O backend deve iniciar a partir de `backend` para manter configuração/storage previsíveis.

Com o backend iniciado, em outro terminal, a partir da raiz:

```bash
cd backend
.venv/bin/python scripts/seed_demo.py --cenario apresentacao
```

Anote os IDs impressos da conta, cálculo, ordem, maker e checker. O seed usa a API
real em `127.0.0.1:8000`, só cria registros ausentes e não altera os existentes.
Não faz upload, processamento, validação nem aprovação. Não roda na inicialização.
É idempotente em execuções sequenciais; não execute duas instâncias simultaneamente.
Em falha parcial, os registros criados ficam preservados; corrija e execute novamente.

O cenário `apresentacao` preparado nesta verificação possui conta **2**, cálculo **2**
e ordem **2** pendente, sem documentos. Maker **1**, checker **2** (R$ 1.000,00)
e usuário com limite baixo **3** (R$ 100,00). IDs dependem do banco: sempre confira
os IDs e a situação impressos, não os assuma em outro ambiente.

Para repetir após aprovar, use um novo nome, por exemplo `--cenario apresentacao-2`.
Isso cria outra conta/cálculo/ordem e reaproveita a estrutura fictícia, sem apagar
histórico nem voltar ordens aprovadas para pendente. Execuções repetidas do seed
não duplicam esses cadastros; uploads voluntariamente repetidos criam novos documentos.

PDFs prontos: `backend/demo/conta_demo.pdf` e `backend/demo/conta_demo_ocr.pdf`.
O segundo é rasterizado, sem camada textual, para demonstrar OCR real. Para regenerar:

```bash
.venv/bin/python scripts/generate_demo_pdf.py
```

Confira `http://127.0.0.1:8000/health`: `database` deve ser `connected`.

## 2. Iniciar backend

Na raiz, terminal 1:

```bash
./scripts/start_backend.sh
```

Equivalente: em `backend`, `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
PostgreSQL precisa estar em execução; o script não inicia banco nem aplica migrations.

## 3. Iniciar frontend web

Na raiz, terminal 2:

```bash
bash scripts/start_frontend.sh
```

Equivalente: em `frontend`, `npm run dev`.
Vite usa `127.0.0.1:5173`; a API padrão é `http://127.0.0.1:8000`.
Se `VITE_API_URL` estiver configurada, confira esse endereço e reinicie Vite.
Não inicie `npm run dev` separadamente: Tauri já o inicia.

## 4. Sequência de cliques

1. **Dashboard → Atualizar**: mostrar totais reais e abrir a conta pelo ID anotado
   (também disponível em **Contas → #ID · Abrir**).
2. **Selecionar PDF**: escolher `backend/demo/conta_demo.pdf`; **Enviar PDF**.
3. No documento recebido, **Processar**; aguardar sucesso e atualização da tabela.
4. Conferir cinco campos: competência `2026-10`, vencimento `2026-10-20`,
   valor `123.45`, consumo `100.500` e código de barras com 44 zeros.
5. Em consumo, editar para `101.000` e **Enviar correção**. Nos demais campos,
   **Confirmar original**. Conferir situações validadas e original preservado.
   Use ponto decimal e data ISO nos campos normalizados.
6. Conferir **Cálculos vinculados**: inicial/calculado R$ 123,45.
7. Em **Ordens vinculadas → #ID · Abrir**, mostrar valor, criador, situação e item.
8. **Aprovar / rejeitar →**: executar os dois bloqueios da seção 6.
9. Selecionar **Pessoa fictícia checker · DEMO-checker**, conferir R$ 1.000,00,
   opcionalmente preencher observação e **Aprovar**.
10. Conferir confirmação, situação **aprovada** e histórico; abrir a ordem novamente.
11. Voltar ao **Dashboard → Atualizar** para mostrar os totais após a decisão.

Opcional: repetir upload/processamento com `conta_demo_ocr.pdf` para mostrar confiança
80% em vez de 95%. Cada documento possui seus próprios campos para revisão.

## 5. O que explicar em cada tela

- Dashboard: agregação de registros persistidos, sem mocks.
- Conta/documento: PDF local, upload real e processamento no backend; OCR não usa serviço externo.
- Validação: extração sugere; pessoa confirma/corrige, preservando o valor original.
- Cálculo: cadastro manual previamente preparado, sem acréscimos; não há motor financeiro.
  A correção de consumo ilustra revisão sem alterar o valor demonstrativo de R$ 123,45.
- Ordem: vínculo com cálculo, item e criador; sistema de pagamento é apenas um cadastro.
- Aprovação: separação entre criador e checker, com alçada verificada pelo backend.

## 6. Erros intencionais

- Escolher **DEMO-maker → Aprovar**: mensagem de autoaprovação bloqueada, HTTP 409.
- Escolher **DEMO-limite-baixo → Aprovar**: alçada R$ 100,00 inferior à ordem
  R$ 123,45, mensagem de alçada insuficiente, HTTP 403.
- Após cada erro, conferir ordem ainda pendente e nenhuma nova decisão no histórico.
  Depois escolher checker; não alterar criador, valor ou alçada para contornar regras.

## 7. Encerramento

Mostrar ordem aprovada e histórico. Explicar que aprovação não significa pagamento
transmitido/liquidado. Fechar a janela e usar Ctrl+C nos terminais para encerrar
Tauri/Vite e backend. Registros e arquivos permanecem para consulta.

## 8. Limitações e verificação realizada

- Sem autenticação; seletor de usuário demonstra papéis, não comprova identidade.
- Cálculo, ordem e item foram preparados manualmente pelo seed usando CRUDs existentes.
  Validação não atualiza conta, cálculo, ordem ou situação agregada da extração.
- Confianças 95%/80% são heurísticas. API não informa estratégia textual/OCR.
- Nenhuma integração BB, SISBB, Plataforma BB ou liquidação; sem deploy.
- CORS permite as quatro origens locais existentes; CSP permite API local na porta 8000.
- Cenários de ensaio ficam no banco e entram nos totais do Dashboard.

Verificação em 06/10/2026: fluxo HTTP real sobre PostgreSQL com upload dos dois PDFs,
OCR real, cinco campos, correção, reprocessamento preservando revisão, listagens,
bloqueios 409/403 e aprovação 201. Desktop Tauri iniciou junto com backend e carregou
registros reais; controles de Dashboard, conta, upload, processamento, validação,
ordem e aprovação foram operados pela acessibilidade da sessão gráfica. Mensagens
de autoaprovação, alçada insuficiente e sucesso/status aprovado foram conferidas
visualmente. Isso é um ensaio pela interface real, não uma apresentação humana.
A conta de apresentação foi preservada sem documentos, com ordem pendente.

Validação final: 115 testes backend passaram; `npm run build`, `npm run lint`,
`npm run type-check` e `git diff --check` passaram. O seed foi repetido com os
mesmos IDs. Nenhum bug de contrato frontend/backend foi encontrado. O PDF OCR
foi compactado para ficar abaixo do limite de upload (79.525 bytes).
Sem commit ou push.
