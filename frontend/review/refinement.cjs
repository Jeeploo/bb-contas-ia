// Revisão real de UI + API, login por cookie, base temporária; sem IA.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/jefferson-ferreira/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome'});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[]; let aiCalls=0;
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('request',r=>{if(r.url().includes('processar-inteligente')) aiCalls++;});
  const base='http://127.0.0.1:5179';
  const api='http://127.0.0.1:8009/api/v1';
  async function login(profile,n) {
   await page.goto(base+'/');
   await page.locator('select[aria-label="Matrícula"]').selectOption(profile);
   await page.getByLabel('Senha',{exact:true}).fill(String(n));
   await page.getByLabel('2º fator',{exact:true}).fill(String(n));
   await page.getByRole('button',{name:'Entrar',exact:true}).click();
   await page.getByRole('heading',{name:'Pagamento de faturas'}).waitFor();
  }
  async function logout(){await page.getByRole('button',{name:'Sair',exact:true}).click();await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();}
  async function nav(name){await page.getByRole('link',{name,exact:true}).click();}
  async function countFaturas(n){const response=await page.request.get(api+'/faturas');assert.equal(response.status(),200);assert.equal((await response.json()).length,n);}
  await login('DEMO-maker',1);
  await page.getByRole('heading',{name:'Resumo da fatura'}).waitFor();
  assert.equal(await page.locator('.summary-card object:visible').count(),0);
  assert.equal(await page.locator('.summary-card details[open]').count(),0);
  await page.screenshot({path:'/tmp/bb-refinamento-resumo.png',fullPage:true});
  await page.getByRole('button',{name:'Enviar para validação',exact:true}).click();
  await page.getByRole('button',{name:'Calcular fatura',exact:true}).click();
  await page.getByRole('heading',{name:'Processamento concluído'}).waitFor();
  await countFaturas(0);
  // Maker encerra a jornada visual: uma devolução futura deve reabri-la.
  await page.getByRole('button',{name:'Nova fatura',exact:true}).first().click();
  await logout();await login('DEMO-checker',4);await nav('Checker');
  await page.locator('.checker-card').waitFor();
  assert.equal(await page.locator('.checker-card').count(),1);
  await page.locator('.checker-toggle').click();
  await page.getByRole('button',{name:'Devolver para ajuste',exact:true}).click();
  await page.getByRole('alert').filter({hasText:'Informe o motivo'}).waitFor();
  await page.getByLabel('Motivo da devolução',{exact:true}).selectOption('Valor divergente');
  await page.getByLabel('Observação',{exact:true}).fill('Corrigir valor para 700,00');
  await page.getByRole('button',{name:'Devolver para ajuste',exact:true}).click();
  await page.locator('.checker-card').waitFor({state:'detached'});
  await countFaturas(0);
  await logout();await login('DEMO-maker',1);
  await page.getByText('Devolvida pelo Checker',{exact:true}).waitFor();
  await page.getByText('Motivo: Valor divergente',{exact:false}).waitFor();
  await page.getByRole('button',{name:'Editar dados',exact:true}).click();
  await page.getByLabel('Valor da fatura',{exact:true}).fill('700.00');
  await page.getByRole('button',{name:'Salvar alterações',exact:true}).click();
  await page.getByRole('dialog').waitFor({state:'hidden'});
  await page.reload();
  await page.getByRole('heading',{name:'Resumo da fatura'}).waitFor();
  await page.getByRole('button',{name:'Enviar para validação',exact:true}).click();
  await page.getByRole('button',{name:'Calcular fatura',exact:true}).click();
  await page.getByRole('heading',{name:'Processamento concluído'}).waitFor();
  await logout();await login('DEMO-checker',4);await nav('Checker');
  await page.locator('.checker-card').waitFor();await page.locator('.checker-toggle').click();
  await page.getByRole('button',{name:'Aprovar',exact:true}).click();
  await page.locator('.checker-card').waitFor({state:'detached'});
  await countFaturas(1);
  const approved=(await (await page.request.get(api+'/faturas')).json())[0];
  const currentUser=(await (await page.request.get(api+'/auth/sessao')).json()).usuario;
  assert.equal(approved.confirmado_por,currentUser.nome);
  assert.equal(approved.prefixo,'REC-DEMO');
  assert.equal(Number(approved.valor),773.05);
  assert.ok(!Number.isNaN(Date.parse(approved.data_confirmacao)));
  const journey=await (await page.request.get(api+`/documentos/${approved.id_fatura}/jornada`)).json();
  assert.equal(approved.solicitado_por,journey.maker);
  const decisions=journey.processamento.extracao.historico_validacao_documental.filter(h=>h.evento==='DECISAO_CHECKER');
  assert.equal(decisions.length,2);assert.equal(decisions[0].motivo,'Valor divergente');
  assert.ok(Array.isArray(decisions[0].campos));assert.ok(Array.isArray(decisions[0].itens));
  await nav('Faturas');
  await page.getByRole('columnheader',{name:'Confirmado por',exact:true}).waitFor();
  await page.locator('tbody tr').first().waitFor();
  const headers=await page.locator('th').allTextContents();
  assert.ok(!headers.includes('Status'));assert.ok(headers.includes('Solicitado por'));assert.ok(headers.includes('Data da confirmação'));
  assert.equal(await page.getByText('Enviar fatura',{exact:true}).count(),0);
  await page.screenshot({path:'/tmp/bb-refinamento-faturas.png',fullPage:true});
  await nav('Relatórios');
  await page.getByRole('img',{name:'Gasto mensal',exact:true}).waitFor();
  const report=await (await page.request.get(api+'/relatorios/resumo')).json();
  assert.equal(report.quantidade,1);assert.equal(Number(report.energia),523);assert.equal(Number(report.agua),0);
  assert.equal(Number(report.valor_total),773.05);
  await page.getByLabel('Tipo da conta',{exact:true}).selectOption('agua');
  await page.getByText('Nenhuma fatura aprovada no período selecionado.',{exact:true}).waitFor();
  await page.getByLabel('Tipo da conta',{exact:true}).selectOption('energia');
  await page.getByRole('img',{name:'Consumo mensal de energia',exact:true}).waitFor();
  await page.getByLabel('Início',{exact:true}).fill('2027-01-01');
  await page.getByText('Nenhuma fatura aprovada no período selecionado.',{exact:true}).waitFor();
  await page.getByLabel('Início',{exact:true}).fill('');
  await page.getByRole('img',{name:'Gasto mensal',exact:true}).waitFor();
  const prefixSelect=page.getByLabel('Prefixo',{exact:true});
  const otherPrefix=await prefixSelect.locator('option').filter({hasText:'PAU-DEMO'}).getAttribute('value');
  await prefixSelect.selectOption(otherPrefix);
  await page.getByText('Nenhuma fatura aprovada no período selecionado.',{exact:true}).waitFor();
  await prefixSelect.selectOption('');
  await page.getByRole('img',{name:'Gasto mensal',exact:true}).waitFor();
  await page.screenshot({path:'/tmp/bb-refinamento-relatorios.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  await page.screenshot({path:'/tmp/bb-refinamento-mobile.png',fullPage:true});
  assert.equal(aiCalls,0);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({fluxo_completo:true,autenticacao_real:true,base:'SQLite temporário',leitura:'persistida',chamadas_ia:aiCalls,relatorio:report,erros:errors}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
