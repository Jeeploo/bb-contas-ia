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
   await page.getByLabel('Matrícula',{exact:true}).fill(matricula);
   await page.getByLabel('Senha',{exact:true}).fill(credentials[matricula].senha);
   await page.getByLabel('2º fator',{exact:true}).fill(credentials[matricula].segundo_fator);
   await page.getByRole('button',{name:'Entrar',exact:true}).click();
   await page.getByRole('heading',{name:'Pagamento de faturas'}).waitFor();
  }
  const base=process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
  await page.goto(base+'/pagamentos');
  await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();
  await login('DEMO-maker');
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
  // Upload real apenas; nenhuma leitura externa. Confere o contexto persistido no backend.
  await page.locator('input[type=file]').setInputFiles('/home/jefferson-ferreira/Downloads/001763932016.pdf');
  const requestPromise=page.waitForRequest(r=>r.url().includes('/documentos/upload'));
  const uploadPromise=page.waitForResponse(r=>r.url().includes('/documentos/upload'));
  await page.getByRole('button',{name:'Iniciar processamento'}).click();
  const req=await requestPromise;const uploaded=await (await uploadPromise).json();
  assert.equal(new URL(req.url()).searchParams.has('id_usuario'),false);
  assert.equal(uploaded.id_conta,null);
  await page.getByRole('heading',{name:'Upload da fatura',exact:true}).waitFor();
  await page.screenshot({path:'/tmp/bb-auth-multi.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.equal(errors.length,0,errors.join('\n'));
  assert.equal(aiCalls,1); // Requisição interceptada e abortada ANTES de chegar ao backend.
  await page.getByRole('button',{name:'Sair',exact:true}).click();
  await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();
  console.log('Login Recife, persistência, logout, rotas protegidas, multi-prefixo e upload autenticado: OK. Nenhuma chamada à IA. Documento de conferência:',uploaded.id_documento);
 } finally { await browser.close(); }
})().catch(e=>{console.error(e.message);process.exitCode=1});
