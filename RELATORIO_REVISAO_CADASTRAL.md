# Revisão documental e resolução cadastral

A causa do bloqueio era a exigência simultânea de `VALIDO` e `documento.id_conta` no botão. A conta só é criada depois da resolução cadastral. Além disso, o envio anterior sempre tentava calcular, misturando confirmação documental e autorização financeira.

O backend agora retorna `pendencias` com `tipo`, `mensagem`, campo quando aplicável, `bloqueia_envio_validacao` e `bloqueia_calculo`, além das decisões agregadas `permite_envio_validacao` e `bloqueia_calculo`. O frontend usa a decisão estruturada, sem interpretar texto livre ou usar apenas o enum documental. Extrações antigas são revalidadas deterministicamente antes de exibir a decisão; nenhuma nova leitura IA é necessária.

A ausência ou ambiguidade de correspondência da concessionária permite envio quando os dados documentais mínimos estão completos e válidos. Permanecem bloqueantes: documento/região não suportados, contexto ausente ou incompatível, divergência de prefixo, campos obrigatórios ausentes/inválidos, duplicação de campos, inconsistência de serviço e ausência de vínculo ativo da unidade consumidora. Falhas de arquivo/leitura continuam sendo rejeitadas pelo fluxo existente.

`POST /extracoes_inteligentes/{id}/enviar-validacao` revalida o documento e exige confirmação dos campos. Registra `ENVIADO_PARA_VALIDACAO` no histórico existente e mantém `revisao_cadastral_pendente`, `EVIDENCIA_INSUFICIENTE`, dados originais e valores confirmados. Não cria concessionária nem conta com ID inventado. Usa as estruturas JSON e de status existentes; nenhuma migração ou alteração de infraestrutura.

O cálculo contextualizado rejeita pendências bloqueantes, inclusive para documento ligado a conta preexistente. As estratégias, valores e regras financeiras existentes não foram alterados. O fluxo legado sem contexto mantém seu comportamento anterior.

A resolução permanece humana: o cadastro administrativo existente e a revalidação determinística podem resolver a correspondência posteriormente. Não foi criada uma nova tela administrativa nem cadastro automático. A resolução completa ainda exige correspondência de serviço, unidade consumidora ativa e prefixo compatível.

`DocumentaryAlerts` apresenta cada pendência separadamente, o nome extraído e a orientação específica. O componente `Alert` centraliza variantes `info` (azul), `warning` (amarelo suave), `review` (#FEF2F2, #FECACA, #B91C1C) e `error` (vermelho mais forte), com ícone discreto e sem alterar o layout da aplicação. A confirmação do envio aparece separadamente, mantendo visível a pendência cadastral.

Foram adicionados três testes backend: envio cadastral com preservação/auditoria e bloqueio real de cálculo, impedimentos estruturais e exigência de confirmação documental. A expectativa explícita do contrato anterior foi atualizada para os campos aditivos. No frontend, quatro testes novos cobrem mensagens/variante, decisão estruturada, múltiplas pendências e variantes do alerta.

A referência real em `/tmp/bb-real-response.json` foi reutilizada em SQLite isolado pela API de interpretação estruturada, confirmação e envio, sem chamada ao provedor IA. No navegador, o script `frontend/review/review-cadastral.cjs` reproduz essa resposta e verifica cor, botão habilitado, envio sem cálculo, três casos de bloqueio e múltiplas pendências. Capturas locais: `/tmp/bb-revisao-cadastral-antes.png` e `/tmp/bb-revisao-cadastral-enviada.png`.

A verificação é local e isolada; o documento no ambiente publicado não foi alterado. Nenhum deploy, commit ou push foi realizado.

## Resultado final das verificações

- Backend: **343 testes, todos aprovados**, incluindo os três novos testes de revisão e a suíte anterior.
- Frontend: **7 testes, todos aprovados**, quatro deles novos.
- Build de produção: aprovado (`tsc -b && vite build`).
- Lint: aprovado (`eslint .`).
- Navegador: roteiro anterior de documento/prefixos/edição/tela estreita aprovado; novo roteiro cadastral e bloqueios estruturais aprovado.
- Referência real: um teste adicional isolado reutilizou os dados salvos e confirmou envio, revisão pendente e cálculo bloqueado, sem IA.
- `git diff --check`: aprovado.
