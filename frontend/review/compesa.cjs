// Dados informados do caso COMPESA, persistidos em SQLite isolado. Auth/backend reais.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH || '/home/jefferson-ferreira/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome'});
  try {
    const page = await browser.newPage();
    const backend = 'http://127.0.0.1:8008';
    let lists = 0, aiCalls = 0;
    const login = await page.request.post(backend+'/api/v1/auth/login', {data:{matricula:'DEMO-maker', senha:'1', segundo_fator:'1'}});
    assert.equal(login.status(), 200);
    await page.route('**/api/v1/**', async route => {
      const req = route.request(), url = new URL(req.url());
      if (url.pathname.endsWith('/concessionarias/elegiveis/associacao')) {
        lists++;
        return route.fulfill({status:403,json:{detail:'Cadastro administrativo indisponível no acesso DEMO.'}});
      }
      if (/processar|interpretacao/.test(url.pathname)) { aiCalls++; throw Error('Nova leitura proibida'); }
      const response = await route.fetch({url:backend+url.pathname+url.search});
      await route.fulfill({response});
    });
    await page.goto(process.env.REVIEW_URL || 'http://127.0.0.1:5173/pagamentos');
    await page.getByRole('heading',{name:'Resumo da fatura',exact:true}).waitFor();
    assert.equal(lists,0);
    assert.equal(await page.locator('.documentary-alert-warning').count(),2);
    assert.equal(await page.locator('.documentary-alert-error').count(),0);
    await page.getByText('8 m³',{exact:true}).waitFor();
    const send = page.getByRole('button',{name:'Enviar para validação',exact:true});
    assert.equal(await send.isEnabled(),true);
    await page.screenshot({path:'/tmp/bb-compesa-resumo.png',fullPage:true});
    await send.click();
    await page.getByRole('button',{name:'Calcular fatura',exact:true}).waitFor();
    assert.equal(lists,0);
    await page.getByRole('button',{name:'Associar concessionária (opcional)',exact:true}).click();
    await page.getByRole('dialog').getByText('Associação cadastral não disponível no ambiente DEMO. A leitura e o processamento podem continuar normalmente.').waitFor();
    assert.equal(lists,1);
    assert.equal(await page.getByRole('dialog').locator('.documentary-alert-error').count(),0);
    await page.getByRole('button',{name:'Cancelar',exact:true}).click();
    assert.equal(await page.locator('.documentary-alert-error').count(),0);
    assert.equal(await page.getByRole('button',{name:'Calcular fatura',exact:true}).isEnabled(),true);
    await page.getByRole('button',{name:'Calcular fatura',exact:true}).click();
    await page.getByRole('heading',{name:'Processamento concluído',exact:true}).waitFor();
    await page.screenshot({path:'/tmp/bb-compesa-concluido.png',fullPage:true});
    const persisted = await (await page.request.get(backend+'/api/v1/documentos/jornada/atual')).json();
    assert.equal(persisted.calculo.valor_inicial,'92.66');
    assert.equal(persisted.processamento.extracao.situacao_validacao,'processamento_concluido');
    assert.equal(persisted.processamento.campos_encontrados.find(f=>f.campo_identificado==='competencia').valor_validado,'2026-08');
    assert.equal(lists,1);
    await page.getByRole('link',{name:'Checker',exact:true}).click();
    await page.getByRole('heading',{name:'Checker — faturas processadas'}).waitFor();
    await page.getByText('COMPANHIA PERNAMBUCANA DE SANEAMENTO',{exact:true}).first().waitFor();
    assert.equal(aiCalls,0);
    console.log(JSON.stringify({caso:'COMPESA (dados informados)',etapas:['Resumo','Validação e cálculo','Processamento concluído','Checker'],listagem_automatica:0,listagem_opcional_403:lists,chamadas_gemini:aiCalls}));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
