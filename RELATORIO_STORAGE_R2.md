# Storage externo de documentos — Cloudflare R2

Implementação concluída sem deploy, criação de bucket/conta, chamada real ao R2 ou execução Gemini/OpenAI. Não houve commit/push, mudança de cálculo/regras de negócio ou alteração visual do frontend.

## Arquitetura

O contrato existente `DocumentStorage` (`save`, `read`, `delete`) foi mantido e passou a declarar o provider. `LocalDocumentStorage` conserva os uploads/arquivos locais existentes. `R2DocumentStorage` usa somente operações S3 compatíveis por boto3/botocore. A factory resolve o storage de novos uploads pela configuração e o storage de leitura pela metadata de cada Documento.

Dependências fixadas: `boto3==1.43.123` e `botocore==1.43.123`. O cliente usa SigV4, região `auto`, credenciais explícitas, leitura limitada, fechamento do stream e uma tentativa por operação. Instanciar o adapter não cria bucket nem faz requisição. Não existe fallback automático para local quando R2 falha.

## Configuração

```dotenv
# Desenvolvimento padrão
DOCUMENT_STORAGE_PROVIDER=local
DOCUMENT_STORAGE_PATH=./storage/documentos
```

```dotenv
# Ambiente externo futuro
DOCUMENT_STORAGE_PROVIDER=r2
R2_ENDPOINT=https://ACCOUNT_ID.r2.cloudflarestorage.com
R2_BUCKET=bb-contas-demo
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_REGION=auto
```

O exemplo não contém segredos válidos. R2 só é ativado explicitamente e exige endpoint HTTPS, bucket, credenciais e região. Em R2, `DOCUMENT_STORAGE_PERSISTENT` pode permanecer false e não é exigido caminho local absoluto/volume. Para local em ambiente externo, a proteção anterior de exigir volume persistente continua valendo.

As credenciais R2 pertencem exclusivamente ao backend. Não colocar valores em `VITE_*`, URL pública, logs, documentação versionada ou banco de documentos.

## Fluxo e referências persistidas

Upload → validação de tamanho/extensão/MIME/conteúdo → `DocumentStorage.save` → referência no PostgreSQL. O nome original não identifica o objeto. A chave R2 é `documentos/<uuid>/<sha256>.<extensão>`, sem unidade consumidora, código de barras ou dados pessoais no nome.

A migration aditiva `e61d4b902f30` acrescenta:

- `documentos.storage_provider`, padrão `local`;
- `documentos.storage_key`, com cópia exata de `caminho_arquivo` nos registros existentes.

Nenhum arquivo é apagado, renomeado ou enviado ao R2 pela migration. `caminho_arquivo` foi preservado no contrato da API como referência lógica compatível; para novos R2, contém a mesma chave de objeto, sem caminho absoluto. A metadata nova é interna ao backend, sem exigir alteração no frontend.

Para registros antigos sem `storage_key`, a leitura usa a referência original. Documentos locais continuam locais mesmo quando o default de novos uploads é R2. Documentos R2 continuam no R2 se o default voltar a local, desde que a configuração de acesso R2 seja mantida. Mudar o bucket/endpoint não migra documentos antigos.

O downgrade é bloqueado enquanto houver registros R2, evitando que uma versão antiga tente ler objetos externos como arquivos locais. A migration foi aplicada somente no PostgreSQL local; os testes também executam migrations reais em banco SQLite temporário.

## Integração com IA, hash e reprocessamento

`DocumentStorage.read` retorna bytes, diretamente para o provider inteligente. Não depende de URL pública ou de gravar um temporário local. O código existente calcula SHA-256 desses bytes e reaproveita a extração quando o hash coincide; reprocessamento explícito mantém o vínculo/ContaConsumo sem duplicar a conta.

Gemini e OpenAI foram preservados. Os testes verificam que ambos os providers simulados recebem os mesmos bytes/MIME oriundos do storage. O processamento determinístico legado também resolve o storage pelo documento.

Objeto ausente gera erro de arquivo indisponível. Falhas técnicas do storage são sanitizadas e retornam 503; não são confundidas com documento inválido. Erros do SDK não incluem credenciais, endpoint sensível ou conteúdo em respostas/logs. O SDK não cria/lista buckets, altera política/ACL nem gera URL pública/presigned.

## Permissões e consistência

Quando houver autorização futura, usar bucket privado e credenciais restritas aos objetos desse bucket. As operações necessárias são `PutObject`, `GetObject` e `DeleteObject`. Delete já é necessário para compensar falha transacional após upload bem-sucedido; não foi criado endpoint público de exclusão.

O backend tenta remover o objeto novo quando a transação no PostgreSQL falha. Se a limpeza também falhar, preserva o erro original e registra somente aviso técnico. Não existe transação distribuída PostgreSQL/R2: falha ambígua de rede pode deixar objeto órfão. Reconciliação/retention/backup deve ser planejada antes de uso prolongado. Nenhuma política destrutiva foi criada.

Não habilitar acesso público R2, domínio público de bucket ou DEBUG de boto3/botocore. O navegador não acessa R2 diretamente, portanto não precisa de CORS público no bucket.

## Arquivos alterados nesta etapa

- `backend/app/processing/storage.py`: contrato, factory e resolução por documento.
- `backend/app/processing/r2_storage.py`: implementação S3/R2 privada.
- `backend/app/core/config.py` e `backend/.env.example`: seleção local/R2 e validação.
- `backend/app/models/documento.py`: metadata de storage.
- `backend/migrations/versions/e61d4b902f30_document_storage.py`: migration aditiva/backfill seguro.
- `backend/app/services/processamento_documento.py`: upload/compensação e leitura pelo storage correto.
- `backend/app/services/leitura_inteligente.py`: bytes do storage e falha técnica sanitizada.
- `backend/app/services/exceptions.py` e `backend/app/api/__init__.py`: erro de storage/HTTP 503.
- `backend/requirements.txt`: boto3/botocore.
- `backend/tests/test_r2_storage.py`: 18 testes novos.
- `DEPLOY.md`, READMEs e este relatório: arquitetura/configuração/limites atualizados.

As alterações anteriores presentes no workspace foram preservadas.

## Testes e validação

**340 testes backend aprovados**, incluindo os 322 anteriores e 18 novos. Novos cenários: salvar/ler/remover local; salvar/ler/remover R2; chave/hash e ausência de nome original; stream fechado e limite por header/bytes; arquivo ausente; erros de provider sanitizados; validação antes do SDK; credenciais explícitas/configuração sem rede; host efêmero com R2; bytes/MIME para Gemini/OpenAI simulados; idempotência e reprocessamento; legado local; alteração do default sem redirecionar documento; upload legado; rollback e migration real preservando arquivo/backfill/downgrade seguro.

Cliente S3 e providers IA foram simulados. Os testes novos bloqueiam conexões de rede, exceto que migrations usam SQLite local sem sockets. Nenhum bucket ou chamada real R2/IA foi utilizado.

Frontend: **3 testes aprovados, lint e build aprovados** com `VITE_API_URL=https://api.exemplo.com`. `git diff --check` passou. `pip check` não encontrou dependências quebradas.

## Arquitetura final e pendências

Principal: **Cloudflare Pages → Render Free → Neon Free + R2 privado → Gemini**. Backend pode usar filesystem efêmero para os documentos novos R2. Railway permanece como alternativa ao Render, sem precisar de volume para os objetos R2.

Ainda será necessário autorizar/criar a infraestrutura, configurar secrets/permissões, validar cookies/domínios e observar franquias/cold starts. Nenhum teste de conectividade real com R2 foi realizado, conforme solicitado. Os PDFs locais existentes foram preservados e não convertidos: para levá-los a um host efêmero, planejar uma importação controlada ou manter o storage local disponível. O seed sintético e documentos novos R2 não dependem dessa importação.

O limiter continua em memória e requer um worker/instância; reinícios não apagam sessões no PostgreSQL nem objetos R2, mas limpam o limiter. A prévia continua sendo o arquivo selecionado no navegador, sem download público ou redesign.
