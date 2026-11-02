// PLAYWRIGHT_MODULE=/tmp/bb-alias-review/node_modules/playwright node review/processing-progress.cjs
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH || '/home/jefferson-ferreira/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome'});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1100}});
    await page.clock.install({time:new Date('2026-11-02T12:00:00Z')});
    await page.clock.pauseAt(new Date('2026-11-02T12:00:00Z'));
    const auth={usuario:{id_usuario:1,nome:'Operador',matricula:'DEMO',funcao:'maker'},prefixos:[{id_prefixo:1,codigo_prefixo:'REF',nome:'Unidade'}],id_prefixo_ativo:1,id_prefixo_principal:1,expira_em:'2099-01-01'};
    const extraction={id_extracao:1,id_documento:1,situacao_validacao:'requer_validacao',resultado_validacao_documental:'EVIDENCIA_INSUFICIENTE',bloqueia_calculo:true,pendencias:[]};
    const result={documento:{id_documento:1,id_conta:null},extracao:extraction,campos_encontrados:[{id_dado_extraido:1,campo_identificado:'concessionaria',valor_extraido:'CONCESSIONÁRIA DE TESTE',situacao_validacao:'pendente'}],itens_encontrados:[]};
    let reading, validation, uploads=0, reads=0, failReading=false, uploadFailure=false, hold=true;
    let readingArrived, validationArrived;
    function arrivals(){
      readingArrived=new Promise(resolve=>{reading=resolve;});
      validationArrived=new Promise(resolve=>{validation=resolve;});
    }
    arrivals();
    await page.route('**/api/v1/**',async route=>{
      const path=new URL(route.request().url()).pathname.replace('/api/v1/','');
      let data=[];
      if(path==='auth/sessao') data=auth;
      else if(path==='documentos/upload') {uploads++; if(uploadFailure) return route.fulfill({status:503,json:{detail:'Não foi possível enviar o documento. Tente novamente.'}}); data=result.documento;}
      else if(path.endsWith('/processar-inteligente')) {
        reads++;
        if(failReading) return route.fulfill({status:503,json:{detail:'Não foi possível ler o documento. Tente novamente.'}});
        if(hold) {reading(route);return;}
        data=result;
      } else if(path.endsWith('/revalidar')) {if(hold) {validation(route);return;} data=extraction;}
      await route.fulfill({json:data});
    });
    async function start(){
      await page.goto(process.env.REVIEW_URL || 'http://127.0.0.1:5173');
      await page.locator('input[type=file]').setInputFiles({name:'fatura.png',mimeType:'image/png',buffer:Buffer.from('teste local')});
      await page.getByRole('button',{name:'Iniciar processamento'}).click();
    }
    const progress=page.getByRole('progressbar');
    await start();
    const readRoute=await readingArrived;
    assert.equal(await progress.getAttribute('aria-valuenow'),'0');
    await page.clock.runFor(30000);
    assert.equal(await progress.getAttribute('aria-valuenow'),'78');
    assert.equal(await page.locator('.processing-activity.complete').count(),3);
    assert.equal(await page.locator('.processing-activity.active').count(),1);
    await page.screenshot({path:'/tmp/bb-processing-progress.png',fullPage:true});
    await readRoute.fulfill({json:result});
    const validationRoute=await validationArrived;
    await page.clock.runFor(30000);
    assert.equal(await progress.getAttribute('aria-valuenow'),'94');
    assert.equal(await page.getByRole('button',{name:'Editar dados'}).count(),0);
    const finalResponse=page.waitForResponse('**/revalidar');
    await validationRoute.fulfill({json:extraction});
    await finalResponse;
    // Aguardar o React consumir a resposta antes de avançar o relógio da animação.
    await page.locator('.processing[data-phase=complete]').waitFor();
    await page.clock.runFor(1000);
    assert.equal(await progress.getAttribute('aria-valuenow'),'100');
    assert.equal(await page.locator('.processing-activity.complete').count(),6);
    assert.equal(await page.getByRole('button',{name:'Editar dados'}).count(),0);
    await page.screenshot({path:'/tmp/bb-processing-complete.png',fullPage:true});
    await page.clock.runFor(700);
    await page.getByRole('button',{name:'Editar dados'}).waitFor();
    assert.equal(reads,1);assert.equal(uploads,1);

    // Erro para o progresso e retry começa em zero, sem reenviar upload concluído.
    failReading=true;hold=false;
    await start();
    await page.getByRole('button',{name:'Tentar novamente'}).waitFor();
    const stopped=await progress.getAttribute('aria-valuenow');
    await page.clock.runFor(10000);
    assert.equal(await progress.getAttribute('aria-valuenow'),stopped);
    assert.equal(await page.locator('.processing-activity.error').count(),1);
    assert.ok(await page.getByRole('alert').count());
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:'/tmp/bb-processing-error-mobile.png',fullPage:true});
    failReading=false;
    await page.getByRole('button',{name:'Tentar novamente'}).click();
    assert.equal(await progress.getAttribute('aria-valuenow'),'0');
    await page.locator('.processing[data-phase=complete]').waitFor();
    await page.clock.runFor(6000);
    await page.getByRole('button',{name:'Editar dados'}).waitFor();
    assert.equal(uploads,2);assert.equal(reads,3);

    uploadFailure=true;
    await start();
    await page.getByRole('button',{name:'Tentar novamente'}).waitFor();
    assert.equal(await progress.getAttribute('aria-valuenow'),'0');
    await page.getByRole('button',{name:'Escolher outro arquivo'}).click();
    await page.locator('input[type=file]').waitFor({state:'attached'});
    assert.equal(await progress.count(),0);
    console.log('Processamento: zero inicial, fases, limites 78/94, sucesso a 100 antes do resumo, erro estável, retry e tela estreita aprovados.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
