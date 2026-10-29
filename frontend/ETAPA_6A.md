> Registro histórico da etapa desktop, anterior ao direcionamento web. Para executar o MVP atual, siga o README.

# Demonstração desktop — etapa 6A

O desktop resolve o contexto pelo cadastro do Prefixo e mostra a interpretação normalizada do documento. O usuário valida valores e solicita o cálculo; não seleciona fórmula nem estratégia.

## Contratos e páginas

- Detalhes da conta: contexto, upload/processamento existentes, dados principais da última extração, composição com detalhes expansíveis, validação humana, cálculo contextual, memória e ordens vinculadas.
- Processamento: filas derivadas das listagens. Considera a extração mais recente; competência e valor total validados; componentes exigidos pela regra para composição; perfil, regra e coeficiente disponíveis. A indicação de prontidão é estimativa; o backend continua sendo a autoridade.
- Dashboard: Recebimento → Leitura → Validação → Cálculo → Ordem → Aprovação, com regra aplicada pelo Prefixo.
- Confiança inferior a 80% recebe destaque para revisão humana; esse limiar visual não cria bloqueio de cálculo.

Novos contratos TypeScript: `PerfilProcessamento`, `ItemExtraido`, `MemoriaCalculo`, `RespostaCalculoContextual`, `EstrategiaCalculo`, `Localidade`, `RegraCalculo` e `ItemRegra`. `Calculo` inclui memória anulável para cálculos históricos.

Consumo centralizado em `src/api/`:

- `GET /api/v1/perfis_processamento`
- `GET /api/v1/itens_extraidos`
- `PATCH /api/v1/itens_extraidos/{id}/validacao`: `{}` confirma o original; `{"valor_validado":"378.79"}` corrige apenas o valor validado.
- `POST /api/v1/contas_consumo/{id_conta}/calcular`: sem fórmula, estratégia ou corpo de cálculo.
- `GET /api/v1/localidades`, `/regras_calculo` e `/itens_regra` para contexto e indicação operacional.
- Cálculos e memória são recuperados também pela listagem existente `/calculos`.

## Preparação com o seed 6A

Com o backend local iniciado e PostgreSQL disponível:

```bash
cd backend
.venv/bin/python scripts/seed_demo.py --cenario etapa6a-ui
```

O seed preserva cadastros existentes e prepara Prefixos `DEMO-INTEGRAL`, `DEMO-COEF` e `DEMO-PREDIAL`. O seed também prepara seu cenário legado de ordens; as três contas 6A são calculadas pelo endpoint contextual.

No Tauri, abra Contas e escolha o Prefixo desejado. Envie um PDF fictício contendo, por exemplo, os dados abaixo. São rótulos de informação, não coordenadas ou layout de concessionária real:

```text
DEMONSTRAÇÃO FICTÍCIA — SEM VALIDADE PARA PAGAMENTO
Competência: 09/2026
Vencimento: 20/10/2026
Valor total: R$ 736,53
Consumo: 500 kWh
Código de barras: 00000000000000000000000000000000000000000000
Consumo-TUSD | 500 kWh | 0,75758 | 378,79
ENERGIA (TE) | 500 kWh | 0,37320 | 186,60
Bandeira amarela | 13,32
ICMS | 736,53 | 18 | 132,58
PIS | 736,53 | 1,65 | 12,15
COFINS | 736,53 | 7,6 | 55,98
Desconto | 20,00
```

Para demonstrar outro layout, use `USO SIST. DISTR. (TUSD)` no lugar de `Consumo-TUSD`. Ambos aparecem com o tipo normalizado TUSD, conforme interpretação retornada pelo backend.

Processe o documento, revise os cinco campos e os sete itens, confirme ou corrija valores e clique em **Calcular conta**. O dado extraído permanece preservado. Os detalhes expansíveis mostram categoria, quantidade/unidade, valor unitário, base de cálculo e alíquota sem inferir unidades ausentes.

| Cenário | Comportamento verificado | Resultado |
| --- | --- | --- |
| Integral | Valor validado de R$ 736,53 | R$ 736,53 |
| Coeficiente | R$ 736,53 ÷ 0,85 | R$ 866,51 |
| Composição | TUSD 378,79 + TE 186,60 + bandeira 13,32 − desconto 20,00 | R$ 558,71 |

ICMS, PIS e COFINS são exibidos como itens estruturados e registrados como ignorados pela regra de composição atual do seed. O frontend não os inclui por conta própria.

## Verificação realizada

- `npm run build`, `npm run lint`, `npm run type-check` e `git diff --check`: passaram.
- `npm run tauri dev`: compilação Rust concluída e janela **BB Contas IA - MVP** aberta e inspecionada.
- Integração local com o seed: upload, processamento, cinco campos, sete itens, validação e memória das três estratégias verificados pela API real.
- Bloqueios antes de validar a competência e por TUSD pendente verificados.
- Conta de composição aberta no Tauri; contexto, campos e itens inspecionados; confirmação de item e cálculo acionados pela interface; nova memória exibida.
- Contas da execução local: #7 integral, #5 coeficiente, #6 composição. IDs são específicos deste banco, não constantes do frontend.
- Backend não alterado nesta implementação; a suíte de 137 testes informada não foi reexecutada.

## Limites

A API atual não retorna text/OCR; a interface informa essa ausência e só mostra estratégia de leitura quando disponível. Cálculos históricos sem memória mostram aviso. A prontidão operacional não substitui a validação definitiva do backend. Não foram reexecutados ordem/aprovação e maker/checker nesta etapa. Os PDFs de verificação foram gerados em `/tmp`; o exemplo acima permite reproduzir o conteúdo.

Nenhum commit ou push foi realizado.
