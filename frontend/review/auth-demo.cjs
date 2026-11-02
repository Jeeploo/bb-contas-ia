// Teste de navegador com backend real. Não chama provider de IA.
// PLAYWRIGHT_MODULE=/path/to/playwright node review/auth-demo.cjs
const { chromium }=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const credentials=JSON.parse(fs.readFileSync(process.env.DEMO_ACCESS_FILE || '/tmp/bb-demo-acessos.json','utf8'));
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];let aiCalls=0;
  page.on('pageerror',e=>errors.push(String(e)));
  await page.route(u=>u.pathname.endsWith('/processar-inteligente'),route=>{ aiCalls++; return route.abort(); });
  async function login(matricula) {
   await page.getByLabel('Matrícula',{exact:true}).selectOption(matricula);
   await page.getByLabel('Senha',{exact:true}).fill(credentials[matricula].senha);
   await page.getByLabel('2º fator',{exact:true}).fill(credentials[matricula].segundo_fator);
   await page.getByRole('button',{name:'Entrar',exact:true}).click();
   await page.getByRole('heading',{name:'Pagamento de faturas'}).waitFor();
  }
  const base=process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
  await page.goto(base+'/pagamentos');
  await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();
  const profiles = page.getByLabel('Matrícula', {exact:true});
  await profiles.locator('option[value="DEMO-maker"]').waitFor({state:'attached'});
  assert.deepEqual(await profiles.locator('option').allTextContents(), ['Selecionar perfil', 'Maker Recife', 'Maker Paulista', 'Maker Multi-Prefixo', 'Checker', 'Alçada reduzida']);
  await page.getByText('Ambiente demonstrativo. Credenciais simplificadas para fins de apresentação.').waitFor();
  await page.screenshot({path:'/tmp/bb-auth-login.png',fullPage:true});
  await profiles.selectOption('DEMO-maker');
  await page.getByLabel('Senha',{exact:true}).fill('9');
  await page.getByLabel('2º fator',{exact:true}).fill('1');
  await page.getByRole('button',{name:'Entrar',exact:true}).click();
  await page.getByRole('alert').filter({hasText:'inválidos'}).waitFor();
  const requestPromise = page.waitForRequest(r => r.url().endsWith('/auth/login'));
  await login('DEMO-maker');
  assert.deepEqual((await requestPromise).postDataJSON(), {matricula:'DEMO-maker', senha:'1', segundo_fator:'1'});
  assert.ok((await page.locator('.greeting').innerText()).includes('Pessoa fictícia maker'));
  assert.equal(await page.getByLabel('Usuário operacional').count(),0);
  assert.equal(await page.getByLabel('Prefixo',{exact:true}).count(),0);
  await page.getByText(/^Prefixo: REC-DEMO/).waitFor();
  await page.reload();await page.getByRole('heading',{name:'Pagamento de faturas'}).waitFor();
  await page.getByText(/^Prefixo: REC-DEMO/).waitFor();
  assert.ok((await page.context().cookies()).some(c=>c.name==='bb_demo_session' && c.httpOnly));
  await page.screenshot({path:'/tmp/bb-auth-maker-recife.png',fullPage:true});
  await page.getByRole('button',{name:'Sair',exact:true}).click();
  await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();
  await page.goto(base+'/faturas');await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();
  await login('DEMO-maker-multi');
  const select=page.getByLabel('Prefixo',{exact:true});
  const options=await select.locator('option').allTextContents();
  assert.equal(options.length,3);assert.ok(options.some(x=>x.includes('REC-DEMO')));assert.ok(options.some(x=>x.includes('PAU-DEMO')));
  const paulista=await select.locator('option').filter({hasText:'PAU-DEMO'}).getAttribute('value');
  await select.selectOption(paulista);
  await page.waitForFunction(()=>document.querySelector('.profile-details').textContent.includes('PAU-DEMO'));
  await page.reload();await page.getByRole('heading',{name:'Pagamento de faturas'}).waitFor();
  assert.equal(await page.getByLabel('Prefixo',{exact:true}).inputValue(),paulista);
  const session=await page.evaluate(async()=>{const r=await fetch('http://'+location.hostname+':8000/api/v1/auth/sessao',{credentials:'include'});return r.json()});
  assert.equal(session.usuario.matricula,'DEMO-maker-multi');assert.equal(session.id_prefixo_ativo,Number(paulista));
  await page.screenshot({path:'/tmp/bb-auth-multi.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.equal(errors.length,0,errors.join('\n'));
  assert.equal(aiCalls,0);
  await page.getByRole('button',{name:'Sair',exact:true}).click();
  await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();
  await page.route(u => u.pathname === '/api/v1/auth/config', route => route.fulfill({json:{demo_mode:false}}));
  await page.reload();
  await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();
  assert.equal(await page.locator('select[aria-label="Matrícula"]').count(),0);
  assert.equal(await page.locator('input[aria-label="Matrícula"]').count(),1);
  assert.equal(await page.getByLabel('Senha',{exact:true}).getAttribute('type'),'password');
  assert.equal(await page.getByLabel('2º fator',{exact:true}).getAttribute('type'),'password');
  assert.equal(await page.getByText('Ambiente demonstrativo. Credenciais simplificadas para fins de apresentação.').count(),0);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  console.log('Login Recife, persistência, logout, rotas protegidas e multi-prefixo: OK. Nenhuma chamada à IA.');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e.message);process.exitCode=1});
