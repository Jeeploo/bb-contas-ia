# Integração documental frontend ↔ backend

## Diagnóstico

`PaymentJourney` carregava contas, prefixos e concessionárias. Exigia escolher uma ContaConsumo, fazia upload em `POST /api/v1/contas_consumo/{id}/documentos/upload` e chamava `POST /api/v1/documentos/{id}/processar`. Esse endpoint usa extração determinística/OCR, sem passar pelo provider Gemini/OpenAI. `UploadArea` apenas selecionava o arquivo.

O resumo inicializava tipo, prefixo e concessionária com os dados da conta escolhida. Assim, a conta DEMO fornecia `DEMO` e `Energia Fictícia Demonstração`, independentemente do conteúdo do PDF. O endpoint legado não fornecia toda a interpretação documental, explicando a ausência de unidade consumidora, concessionária documental e outros campos. `CalculationSummary` mostrava “Aguardando revisão” enquanto não existisse cálculo, mesmo que o valor já estivesse extraído.

O cálculo produz “Competência validada deve usar AAAA-MM” quando `date.fromisoformat(valor_validado + '-01')` rejeita o valor. A revisão do frontend enviava `valor_extraido`, ignorando `valor_normalizado`. O contrato de leitura preserva a representação original da IA e normaliza separadamente: por exemplo, `09/2026` e `2026-09`. Reenviar o original permite exatamente essa incompatibilidade. Agora a resposta inteligente expõe o normalizado, a interface usa helpers únicos e o backend rejeita a competência não canônica na validação, antes do cálculo.

Limite da investigação histórica: as competências persistidas consultadas no banco local estavam canônicas. Não havia um payload inválido persistido que permitisse afirmar qual string provocou especificamente a ocorrência anterior. O defeito de contrato acima foi identificado no código e coberto por regressão com original `09/2026`.

## Fluxo implementado

1. Seleção explícita do usuário operacional no ambiente sem autenticação. Um único usuário ativo é selecionado automaticamente.
2. Consulta dos vínculos ativos e apresentação somente dos prefixos autorizados. Um prefixo único é automático; vários exigem seleção antes do upload.
3. `POST /api/v1/documentos/upload?id_usuario=…&id_prefixo=…` armazena o documento e seu contexto, sem ContaConsumo.
4. `POST /api/v1/documentos/{id}/processar-inteligente?id_usuario=…&id_prefixo=…` executa `LeituraInteligenteService` → provider configurado → normalização/LeituraDocumental → `InterpretacaoDocumentalService` → `ValidacaoDocumentalService`.
5. `ContaConsumoService.criar_da_leitura` cria a conta em situação pendente apenas com resultado `VALIDO`, concessionária resolvida e competência, vencimento e valor disponíveis. Mapeia emissão, código de barras, consumo, unidade, categoria e prefixo. A unidade consumidora completa é preservada em `numero_conta` e no dado extraído.
6. O vínculo Documento → ContaConsumo é estabelecido na mesma transação da leitura. A extração continua vinculada ao documento. O lock do documento e a verificação do vínculo existente evitam duplicação em reprocessamentos.
7. A correção humana mantém o original e grava `valor_validado`. Quando a correção resolve a pendência, ou uma revalidação explícita resolve o cadastro, a conta pode ser criada. O caminho idempotente também tenta criar uma conta que se tornou elegível após revisão cadastral, sem nova chamada ao provider.
8. Cálculo continua exigindo a revisão e as regras já existentes. Maker/checker, cálculo, OpenAI e Gemini foram preservados.

`DOCUMENTO_NAO_SUPORTADO`, `REGIAO_NAO_SUPORTADA`, `DIVERGENCIA_PREFIXO` e `EVIDENCIA_INSUFICIENTE` preservam o documento e a extração, sem inventar conta ou vínculo cadastral. Os endpoints legados continuam disponíveis para compatibilidade; a nova jornada não os utiliza.

A migration `c31f82a104df` torna `documentos.id_conta` opcional e acrescenta as referências de contexto ao documento. Foi aplicada no PostgreSQL local. O downgrade exige resolver documentos sem conta antes de restaurar a obrigatoriedade antiga.

## Apresentação e edição

- Cards principais: tipo, valor, vencimento, competência, prefixo, concessionária, unidade consumidora, consumo e código de barras.
- Contexto documental: município e UF. Outros dados disponíveis incluem emissão, número do documento, endereço, leituras, período, demanda e bandeira.
- Componentes de energia e água usam nome amigável e valor: TUSD, TE, bandeira, iluminação pública, ICMS, PIS, COFINS, tarifas de água/esgoto, serviços, descontos, multas, juros e outros encargos, quando extraídos.
- Valor aparece antes da confirmação humana, com indicação de extração automática.
- Nome da concessionária documental não é substituído pelo cadastro. A correspondência cadastral aparece separadamente.
- Unidade e código de barras recebem máscara apenas na apresentação. Edição, persistência e payload conservam os valores completos.
- `formatCompetenciaDisplay('2026-09')` retorna `09/2026`; `parseCompetenciaDisplay('09/2026')` retorna `2026-09`. Competência inválida é rejeitada; mês inválido também.
- Resultado documental recebe mensagem amigável; não aparece como enum cru.
- Processamento não inventa percentual nem conclusão intermediária que o backend não informou.
- Fallback da prévia não mostra imagem de fatura fictícia. O usuário pode abrir o documento original.

## Validação

Backend: **297 testes passaram**, incluindo toda a suíte existente, com `python -m unittest discover -s tests`. O arquivo `test_documento_inicial.py` acrescenta cinco testes cobrindo upload sem conta prévia, mapeamento/campo normalizado, criação após leitura, idempotência e reprocessamento, estados bloqueados, prefixo único/múltiplos/não autorizado, correção sem perder original, criação após revisão e competência canônica.

Frontend: `npm test` executa dois testes de helpers e renderização do resumo; `npm run build` e `npm run lint` passaram. `review/document-flow.cjs`, executado com Playwright externo, passou nos cenários de prefixo único e múltiplos, upload sem referência, dados no resumo, edição MM/AAAA → payload AAAA-MM, preservação do original, ausência de leitura adicional ao editar e responsividade móvel.

Foi executada uma única chamada real ao Gemini usando `/home/jefferson-ferreira/Downloads/001763932016.pdf`. A API retornou HTTP 200. O navegador mostrou:

| Campo | Resultado |
| --- | --- |
| Valor | R$ 736,53 |
| Competência | 09/2026; interno 2026-09 |
| Vencimento | 20/10/2026 |
| Concessionária | COMPANHIA ENERGÉTICA DE PERNAMBUCO |
| Prefixo contextual | PAU-DEMO |
| Município/UF | PAULISTA / PE |
| Unidade consumidora | ***4-78 |
| Código de barras | ***3653 |
| Consumo | 523 kWh |
| TUSD / TE | R$ 378,79 / R$ 186,60 |
| ICMS / PIS / COFINS | R$ 118,63 / R$ 5,75 / R$ 26,68 |

Nenhum erro JavaScript foi observado. As conferências visuais posteriores reutilizaram a resposta real salva, sem repetir a chamada à IA.

## Limitações e continuidade

O documento real recebeu `EVIDENCIA_INSUFICIENTE`: “Concessionária sem correspondência cadastral unívoca”. Por isso não criou ContaConsumo e não prosseguiu ao cálculo. É necessário resolver a correspondência cadastral real e conferir o vínculo da unidade consumidora com o prefixo. Nenhum cadastro fictício foi criado para desbloquear essa etapa.

A decisão `VALIDO` também precisa dos campos financeiros obrigatórios para materializar ContaConsumo. Evidência incompleta fica no documento/extração em revisão. A tarefa não implementa autenticação; o usuário operacional continua sendo contexto declarado do ambiente local.

No navegador headless, o PDF pode não renderizar dentro de `<object>`; o link para abrir o original permanece disponível. A criação da ContaConsumo foi validada com provider simulado e banco isolado; a leitura real validou o caminho de revisão cadastral pendente.

Sem commit e sem push. A alteração preexistente em `scripts/start_frontend.sh` foi preservada.
