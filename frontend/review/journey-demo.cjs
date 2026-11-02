// Revisão com backend SQLite isolado (journey-server.py) e documento real já persistido.
// PLAYWRIGHT_MODULE=/tmp/bb-alias-review/node_modules/playwright REVIEW_SNAPSHOT=/tmp/bb-jornada-real.json node frontend/review/journey-demo.cjs
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
  const snapshot=JSON.parse(fs.readFileSync(process.env.REVIEW_SNAPSHOT,'utf8'));
  const document=process.env.REVIEW_DOCUMENT || path.resolve('backend/storage/documentos',snapshot.documento.caminho_arquivo);
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH || '/home/jefferson-ferreira/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome'});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1100}});
    let user=1, uploads=0, restores=0, documentId;
    const frontend=process.env.REVIEW_URL || 'http://127.0.0.1:5173';
    const backend=process.env.REVIEW_BACKEND || 'http://127.0.0.1:8007';
    await page.route('**/api/v1/**',async route=>{
      const request=route.request(), url=new URL(request.url()), endpoint=url.pathname.replace('/api/v1/','');
      if(endpoint==='auth/sessao') return route.fulfill({json:{usuario:{id_usuario:user,nome:user===1?'Maker teste':'Checker teste',matricula:'TESTE',funcao:user===1?'maker':'checker'},prefixos:[{id_prefixo:1,codigo_prefixo:'TESTE',nome:'Contexto documental real'}],id_prefixo_ativo:1,id_prefixo_principal:1,expira_em:'2099-01-01'}});
      if(endpoint==='documentos/upload') {
        uploads++;
        // O protocolo de interceptação do Chromium omite os bytes do arquivo multipart.
        const response=await page.request.post(backend+'/api/v1/documentos/upload',{headers:{'x-review-user':String(user)},multipart:{file:{name:path.basename(document),mimeType:'application/pdf',buffer:fs.readFileSync(document)}}});
        if(response.status()>=400) console.log('Upload HTTP',response.status(),await response.text());
        else documentId=(await response.json()).id_documento;
        return route.fulfill({response});
      }
      if(endpoint==='documentos/jornada/atual') restores++;
      const response=await route.fetch({url:backend+url.pathname+url.search,headers:{...request.headers(),'x-review-user':String(user)}});
      if(response.status()>=400) console.log('HTTP',endpoint,response.status(),await response.text());
      await route.fulfill({response});
    });
    const assertStep=async step=>{await page.locator(`.stepper li:nth-child(${step})[aria-current="step"]`).waitFor();};
    async function roundTrip(step) {
      await page.getByRole('link',{name:'Faturas',exact:true}).click();
      await page.getByRole('heading',{name:'Faturas',exact:true}).waitFor();
      await page.getByRole('link',{name:'Pagamentos',exact:true}).click();
      await assertStep(step);
    }
    const beforeStats=await (await page.request.get(backend+'/review/stats')).json();
    await page.goto(frontend+'/pagamentos');
    await page.getByRole('button',{name:'Nova fatura',exact:true}).first().click();
    await page.locator('input[type=file]').setInputFiles(document);
    await page.getByRole('button',{name:'Iniciar processamento',exact:true}).click();
    await page.getByRole('heading',{name:'Resumo da fatura',exact:true}).waitFor().catch(async e=>{ console.log('Alertas:',await page.locator('[role=alert]').allTextContents()); throw e; });
    await assertStep(2);
    assert.equal(await page.locator('.documentary-alert-warning').count(),2);
    assert.equal(await page.locator('.documentary-alert-error').count(),0);
    assert.equal(await page.getByRole('button',{name:'Enviar para validação',exact:true}).isEnabled(),true);
    await page.getByRole('button',{name:'Editar dados',exact:true}).click();
    await page.getByLabel('Consumo',{exact:true}).fill('524');
    await page.getByRole('button',{name:'Salvar alterações',exact:true}).click();
    await page.getByRole('dialog').waitFor({state:'hidden'});
    await roundTrip(2);
    await page.getByText('524 kWh',{exact:true}).waitFor();
    await page.screenshot({path:'/tmp/bb-jornada-resumo.png',fullPage:true});
    await page.getByRole('button',{name:'Enviar para validação',exact:true}).click();
    await assertStep(3);
    await page.getByRole('button',{name:'Calcular fatura',exact:true}).waitFor();
    await roundTrip(3);
    await page.reload();
    await assertStep(3);
    await page.getByRole('button',{name:'Calcular fatura',exact:true}).click();
    await assertStep(4);
    await page.getByRole('heading',{name:'Processamento concluído',exact:true}).waitFor();
    await page.getByText('Regra DEMO — Coeficiente 0,9055',{exact:true}).waitFor();
    await page.getByText('Coeficiente: 0,9055',{exact:true}).waitFor();
    await page.getByText('Regra demonstrativa baseada em um caso real de prefixo específico. Não representa uma regra financeira aplicável a todos os prefixos do Banco do Brasil.',{exact:true}).waitFor();
    const persisted=await (await page.request.get(backend+`/api/v1/documentos/${documentId}/jornada`)).json();
    assert.equal(persisted.calculo.valor_inicial,'736.53');
    assert.equal(persisted.calculo.valor_calculado,'813.40');
    assert.equal(persisted.calculo.memoria_calculo.diferenca,'76.87');
    assert.equal(persisted.calculo.memoria_calculo.expressao,'736.53 / 0.9055');
    assert.equal(persisted.calculo.memoria_calculo.parametros.coeficiente,'0.9055');
    await page.getByText('Ver detalhes do cálculo',{exact:true}).click();
    await page.getByText(/Regra #1/).waitFor();
    await page.screenshot({path:'/tmp/bb-jornada-conclusao.png',fullPage:true});
    await roundTrip(4);
    const resumed=await (await page.request.get(backend+`/api/v1/documentos/${documentId}/jornada`)).json();
    assert.deepEqual(resumed.calculo,persisted.calculo);
    assert.equal(uploads,1);
    const stats=await (await page.request.get(backend+'/review/stats')).json();
    assert.deepEqual(stats,{replays:beforeStats.replays+1,chamadas_ia:0});
    await page.getByRole('button',{name:'Nova fatura',exact:true}).first().click();
    await assertStep(1);
    await roundTrip(1);
    await page.getByRole('link',{name:'Checker',exact:true}).click();
    await page.getByRole('heading',{name:'Checker — faturas processadas'}).waitFor();
    const invoice=page.getByRole('article').filter({has:page.getByRole('heading',{name:new RegExp('^Fatura #'+documentId+' ·')})});
    await invoice.getByRole('button',{name:'Confirmar fatura',exact:true}).waitFor();
    await invoice.getByRole('button',{name:'Confirmar fatura',exact:true}).click();
    await invoice.getByRole('alert').filter({hasText:'Autoaprovação bloqueada'}).waitFor();
    user=2; await page.reload();
    await invoice.getByRole('button',{name:'Confirmar fatura',exact:true}).click();
    await invoice.getByText('Decisão final registrada.',{exact:true}).waitFor();
    await page.screenshot({path:'/tmp/bb-jornada-checker.png',fullPage:true});
    assert.ok(restores>=8);
    // Seleção de prefixo continua acessível antes da primeira consulta; falha de retomada não libera upload.
    const selection=await browser.newPage();
    let selectedPrefix=null, attempts=0, failRestore=true;
    const selectionAuth=()=>({usuario:{id_usuario:1,nome:'Maker teste',matricula:'TESTE',funcao:'maker'},prefixos:[1,2].map(id=>({id_prefixo:id,codigo_prefixo:String(id),nome:'Prefixo teste'})),id_prefixo_ativo:selectedPrefix,id_prefixo_principal:1,expira_em:'2099-01-01'});
    await selection.route('**/api/v1/**',async route=>{
      const endpoint=new URL(route.request().url()).pathname.replace('/api/v1/','');
      if(endpoint==='auth/sessao') return route.fulfill({json:selectionAuth()});
      if(endpoint==='auth/prefixo') { selectedPrefix=route.request().postDataJSON().id_prefixo; return route.fulfill({json:selectionAuth()}); }
      if(endpoint==='documentos/jornada/atual') {
        assert.equal(selectedPrefix,1); attempts++;
        return failRestore ? route.fulfill({status:503,json:{detail:'Indisponibilidade de teste'}}) : route.fulfill({json:{documento:null,processamento:null,calculo:null}});
      }
      throw Error('Endpoint inesperado na seleção: '+endpoint);
    });
    await selection.goto(frontend+'/pagamentos');
    await selection.getByLabel('Prefixo',{exact:true}).waitFor();
    assert.equal(attempts,0);
    await selection.getByLabel('Prefixo',{exact:true}).selectOption('1');
    await selection.getByRole('button',{name:'Tentar recuperar processamento'}).waitFor();
    assert.equal(await selection.locator('input[type=file]').count(),0);
    failRestore=false;
    await selection.getByRole('button',{name:'Tentar recuperar processamento'}).click();
    await selection.locator('input[type=file]').waitFor({state:'attached'});
    assert.ok(attempts>=2);
    await selection.close();
    console.log(JSON.stringify({documento_real:true,backend:'SQLite temporário com regra DEMO 0,9055',upload:uploads,replays:1,chamadas_gemini:0,restauracoes:restores,etapas:[1,2,3,4],nova_fatura:true,valor_calculado:'813.40',diferenca:'76.87',checker_confirmou:true,prefixos_multiplos:true,falha_retomada_recuperavel:true}));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
