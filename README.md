# BB Contas IA

MVP web para leitura inteligente, validação e processamento assistido de contas de consumo de unidades operacionais do Banco do Brasil.

O escopo atual contempla energia elétrica e água/saneamento em documentos de Pernambuco, com leitura assistida por IA, validação determinística, revisão humana e contexto operacional por prefixo. O backend implementa controles Maker/Checker e alçadas. É um MVP de demonstração, sem pagamento bancário real e sem caráter de sistema bancário produtivo.

## Arquitetura

```text
Frontend — React + Vite + TypeScript (Cloudflare Pages)
    ↓ API HTTP
Backend — FastAPI + Python (Render)
    ├── PostgreSQL (Neon): dados estruturados
    ├── Cloudflare R2: PDFs e imagens privados
    └── Gemini: interpretação documental
```

O frontend apresenta a jornada e não executa regras financeiras. O backend concentra regras, validações e decisões críticas determinísticas; a IA interpreta os documentos.

## Stack

| Camada | Tecnologias |
| --- | --- |
| Frontend | React, Vite, TypeScript, React Router, Lucide React |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL |
| Infraestrutura | Cloudflare Pages, Cloudflare R2, Render, Neon |
| IA | Gemini como provider principal do ambiente publicado; abstração preparada para múltiplos providers |

## Ambiente publicado

- Frontend: [bb-contas-ia.pages.dev](https://bb-contas-ia.pages.dev)
- API: [bb-contas-ia.onrender.com](https://bb-contas-ia.onrender.com)
- Health: [/health](https://bb-contas-ia.onrender.com/health)

O Render Free pode entrar em estado de inatividade; a primeira requisição pode demorar alguns segundos.

## Login DEMO

Com `DEMO_MODE=true`, o campo matrícula vira um seletor de perfil. Senha e 2º fator permanecem obrigatórios, e a autenticação continua sendo processada pelo backend. A sessão usa cookie HttpOnly e fornece identidade, prefixos autorizados e permissões. Maker/Checker e alçadas continuam validados no backend.

As credenciais abaixo são deliberadamente fracas, exclusivas do ambiente demonstrativo e destinadas à apresentação pública do MVP. O 2º fator é um código de demonstração; essa autenticação não é adequada para produção.

| Perfil | Senha | 2º fator |
| --- | --- | --- |
| Maker Recife | 1 | 1 |
| Maker Paulista | 2 | 2 |
| Maker Multi-Prefixo | 3 | 3 |
| Checker | 4 | 4 |
| Alçada reduzida | 5 | 5 |

## Jornada da fatura

Upload do documento → leitura pela IA → normalização dos campos → validação determinística → revisão humana → resolução cadastral quando necessária → cálculo elegível → Maker/Checker.

A IA interpreta o documento, mas não decide sozinha sua validade financeira ou cadastral. O cálculo exige contexto autorizado, campos validados e regras elegíveis. O backend oferece o fluxo Maker/Checker; a conclusão da revisão na interface não executa pagamento nem equivale a uma aprovação bancária.

### Revisão cadastral

Uma concessionária não reconhecida não impede, por si só, o envio do documento para revisão quando os demais requisitos documentais estão atendidos. O nome extraído (`concessionaria_extraida`) é preservado, sem inventar `id_concessionaria` e sem cadastrar concessionárias automaticamente pela IA.

O documento pode permanecer em revisão cadastral, com cálculo definitivo bloqueado enquanto a pendência relevante não for resolvida. A resolução humana é seguida de revalidação determinística.

### Storage

A abstração `DocumentStorage` possui implementações local, para desenvolvimento, e Cloudflare R2, para ambiente externo. O PostgreSQL armazena referências e metadados; o R2 guarda o arquivo binário privado. O backend lê o objeto diretamente para processamento, sem necessidade de URL pública do documento.

## Interface

| Rota | Função |
| --- | --- |
| `/` | Acesso DEMO |
| `/pagamentos` | Upload, leitura, resumo, edição, validação e revisão |
| `/faturas` | Histórico e consulta |
| `/relatorios` | Placeholder; relatórios ainda não disponibilizados |

As rotas internas exigem sessão válida. Os principais componentes da jornada, em `frontend/src/components/payment/`, são `AppShell`, `PaymentStepper`, `UploadArea`, `InvoiceSummary`, `ValidationSummary` e `DocumentaryAlerts`, que apresenta pendências documentais e cadastrais.

## Desenvolvimento local

Pré-requisitos: Python com ambiente virtual, Node.js/npm e PostgreSQL configurado. Configure o ambiente do backend conforme [DEPLOY.md](DEPLOY.md), instale suas dependências e prepare o banco antes de iniciar.

Backend, com `.venv` e banco configurados:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

Para autenticação DEMO local, configure `DEMO_MODE=true` no ambiente do backend. Em banco de demonstração, prepare os dados fictícios e os acessos antes de iniciar o servidor:

```bash
cd backend
source .venv/bin/activate
python scripts/seed_demo.py --ambiente-demo
python scripts/prepare_demo_auth.py --ambiente-demo --arquivo /tmp/bb-demo-acessos.json
```

O script `prepare_demo_auth.py` configura os cinco perfis existentes no seed e gera um arquivo privado de acessos. Não versione esse arquivo nem arquivos de ambiente ou credenciais de infraestrutura.

Frontend, em outro terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

`VITE_API_URL` é obrigatória e define a origem da API; o cliente acrescenta `/api/v1`. Para o backend local, use `http://127.0.0.1:8000`. A interface fica disponível em `http://127.0.0.1:5173`.

## Testes e verificação

Estado verificado nesta atualização: **346 testes backend e 7 testes frontend aprovados**, além de lint e build aprovados. Os roteiros de revisão de navegador com Playwright ficam em `frontend/review/`, incluindo jornada documental, revisão cadastral e autenticação DEMO. As revisões documentais usam respostas simuladas; não comprovam, isoladamente, integração com os serviços publicados.

Backend, com o ambiente virtual ativo:

```bash
cd backend
python -m unittest discover -s tests
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Na raiz do repositório:

```bash
git diff --check
```

## Princípios do projeto

- IA interpreta; backend decide. Regras financeiras são determinísticas.
- O usuário vem da sessão, e o prefixo é validado no backend.
- Documentos permanecem privados.
- Nenhuma entidade cadastral é criada automaticamente pela IA.
- Maker não aprova a própria operação.
- O cálculo depende de contexto e validações elegíveis.

## Limitações atuais

- MVP restrito a energia elétrica e água/saneamento, com escopo territorial em Pernambuco.
- Autenticação institucional/SSO não implementada; credenciais DEMO servem apenas à apresentação.
- Resolução cadastral administrativa completa ainda não possui tela própria.
- Relatórios permanecem como placeholder.
- Render Free pode hibernar. O rate limit em memória atende ao processo único da demonstração, sem coordenação entre múltiplas réplicas.
- Não executa pagamento bancário real.

## Documentação complementar

- [Deploy e configuração](DEPLOY.md)
- [Autenticação DEMO](RELATORIO_AUTENTICACAO_DEMO.md)
- [Integração documental](RELATORIO_INTEGRACAO_DOCUMENTAL.md)
- [Storage R2](RELATORIO_STORAGE_R2.md)
- [Revisão cadastral](RELATORIO_REVISAO_CADASTRAL.md)
