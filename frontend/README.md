# BB Contas IA — Desktop MVP

Frontend React + Vite + TypeScript + React Router, empacotado com Tauri v2.
Rust apenas inicia a janela; regras, processamento e persistência permanecem no
FastAPI e no PostgreSQL. Visual próprio, sem reproduzir a identidade oficial.

## Requisitos

- Node 20.20.2 (Node 20 compatível com Vite 6), npm 10.8.2.
- Rust e Cargo instalados; ambiente informado: 1.99.0.
- Linux: GTK 3 e WebKitGTK 4.1 e ferramentas de compilação do Tauri v2.
- Sessão gráfica disponível para abrir o desktop.
- Backend FastAPI na porta 8000, banco PostgreSQL configurado e migrations aplicadas.
- Dependências Python, storage de documentos e OCR conforme
  [FLUXO_DOCUMENTOS.md](../backend/FLUXO_DOCUMENTOS.md).

## Instalação e execução

No diretório `frontend`:

```bash
cp .env.example .env
npm install
npm run dev
```

Web: http://127.0.0.1:5173. A porta é fixa para manter o CORS previsível.
`VITE_API_URL=http://127.0.0.1:8000` aponta para a raiz da API; o client acrescenta
`/api/v1`. A variável é incorporada durante o build. Reinicie Vite após alterá-la.

Backend, em outro terminal, a partir de `backend`, usando o ambiente Python do projeto:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Desktop:

```bash
npm run tauri dev
```

Validação e build:

```bash
npm run build
npm run lint
npm run type-check
npm run tauri build
```

O build Tauri gera o executável em `src-tauri/target/release/`.
Bundles/instaladores estão desativados. Não há updater, assinatura ou plugins extras.
Janela: `BB Contas IA - MVP`, 1440×900, mínimo 900×640.

## Estrutura

- `src/api/`: client HTTP, JSON/multipart, erros e paginação.
- `src/types/`: contratos tipados da API, inclusive decimais serializados como strings.
- `src/components/`: tabela, estados de consulta, badges e revisão dos campos.
- `src/layout/`: sidebar fixa, topo e área principal responsiva.
- `src/pages/`: Dashboard, Contas/detalhes, Processamento, Validações,
  Cálculos, Ordens/detalhes e Aprovações.
- `src-tauri/`: container nativo mínimo e configuração de segurança.
- `public/`: assets estáticos.

HashRouter permite navegação no executável sem depender de fallback do servidor.
As listagens percorrem `offset`/`limit`; o dashboard agrega os registros existentes.
“Documentos processados” conta documentos distintos com extração; “validações
pendentes” conta campos não validados; ordens pendentes excluem aprovadas/rejeitadas.
Todas as consultas possuem carregamento, erro com retry e estado vazio.
Operações exibem confirmação ou erro da API, com bloqueio enquanto são enviadas.

## Fluxo de demonstração

Prepare contas, usuários/alçadas, cálculos, ordens e itens pela API. Veja
[MVP_DEMO.md](../backend/MVP_DEMO.md) para contratos e cenário fictício.
Os testes desse documento usam banco temporário e não populam o PostgreSQL local.

1. Abra **Contas** e os detalhes de uma conta existente.
2. Selecione um PDF e clique **Enviar PDF**.
3. Clique **Processar** no documento recebido.
4. Confira situação, confiança percentual e campos extraídos. Texto bruto não é exibido.
5. Use **Confirmar original** ou edite o valor e **Enviar correção**.
   Apenas `valor_validado` é enviado; o original permanece preservado no backend.
6. Confira cálculos e ordens vinculados nos detalhes da conta.
7. Abra a ordem para consultar seus itens e siga **Aprovar / rejeitar**.
8. Selecione o aprovador, confira sua alçada e registre a decisão.
   Autoaprovação, alçada insuficiente e registros ausentes têm mensagens amigáveis.
9. Atualize o dashboard para conferir os totais.

## Endpoints consumidos

Prefixo `/api/v1`:

- GET: `contas_consumo`, `contas_consumo/{id}`, `documentos`,
  `extracoes_inteligentes`, `dados_extraidos`, `calculos`, `ordens_pagamento`,
  `ordens_pagamento/{id}`, `itens_pagamento`, `aprovacoes`, `usuarios`, `alcadas`,
  `prefixos`, `concessionarias`, `sistemas_pagamento`.
- POST `contas_consumo/{id}/documentos/upload`: multipart com campo `file`.
- POST `documentos/{id}/processar`.
- PATCH `dados_extraidos/{id}/validacao`: `{}` confirma o original;
  `{"valor_validado":"..."}` registra correção.
- POST `aprovacoes`: ordem, usuário, decisão `aprovado`/`rejeitado`, observação e data.

## Limitações

- Sem cadastro administrativo, autenticação ou autorização de identidade na UI.
  O seletor de aprovador é exclusivo da demonstração; a API recebe IDs de usuários.
- Cálculos e ordens são consultados, não criados automaticamente. O backend atual
  não executa motor financeiro. Não há cálculo de negócio no frontend ou Rust.
- Validação não altera ContaConsumo nem a situação agregada da extração.
- O contrato atual não informa estratégia text/OCR. A UI exibe “Não informada
  pela API”; está preparada para mostrar a propriedade opcional quando disponível.
- Não há envio real ao sistema bancário. Aprovação não significa liquidação.
- Consultas de vínculos usam listagens completas por ausência de filtros específicos;
  isso atende ao MVP, mas demanda endpoints agregados/filtrados para alto volume.
- O CSP permite a API local na porta 8000. Se mudar o host no `.env`, ajuste
  `connect-src` em `src-tauri/tauri.conf.json` e configure CORS no backend.
- CORS do backend permite exclusivamente localhost:5173, 127.0.0.1:5173,
  tauri://localhost e http://tauri.localhost. Não usa wildcard.

## Validação nesta implementação

- `npm install`: concluído, auditoria sem vulnerabilidades reportadas.
- `npm run build`, `npm run lint` e `npm run type-check`: aprovados.
- `npm run tauri build`: aprovado, Tauri/CLI 2.12.1; executável Linux gerado.
- `npm run tauri dev`: janela aberta e renderização conferida; processo encerrado
  após a inspeção. O backend estava indisponível nesse momento, e a UI mostrou
  o estado de erro de conexão com opção de tentar novamente.
- Client HTTP: verificados multipart, paginação e mensagens 404/409/403/422/conexão
  com respostas simuladas, sem alterar dados do banco.
- Backend: `python -m unittest discover -s tests` passou nos 115 testes.
- Preflight CORS: quatro origens aceitas e origem externa rejeitada.
- `git diff --check`: aprovado.

A inspeção desktop confirma inicialização e renderização; não substitui uma
execução manual completa com dados demonstrativos no PostgreSQL local.
Downloads npm/crates, testes FastAPI e acesso à sessão gráfica precisaram de
execução fora do sandbox deste ambiente. Nenhum commit ou push foi realizado.
