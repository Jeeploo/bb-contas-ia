// Fixture simulada baseada no nome do caso real. Sem acesso ao documento ou à IA.
// PLAYWRIGHT_MODULE=/tmp/bb-alias-review/node_modules/playwright node review/association.cjs
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async () => {
  const nome = 'COMPANHIA ENERGÉTICA DE PERNAMBUCO';
  const snapshot = {documento:{id_documento:8,id_conta:null},
    extracao:{id_extracao:17,id_documento:8,situacao_validacao:'requer_validacao'},
    campos_encontrados:Object.entries({tipo_documento:'ENERGIA',concessionaria:nome,uf:'PE',municipio:'Recife',unidade_consumidora:'001',competencia:'2026-09',data_vencimento:'2026-10-20',valor_original:'736.53'}).map(([campo_identificado,valor_extraido],i)=>({id_dado_extraido:i+1,campo_identificado,valor_extraido,valor_normalizado:valor_extraido,situacao_validacao:'pendente',id_extracao:17})),itens_encontrados:[]};
  const browser = await chromium.launch({ headless:true, executablePath:process.env.CHROMIUM_PATH || '/home/jefferson-ferreira/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome' });
  try {
    const page = await browser.newPage({ viewport:{width:1440,height:1100} });
    const extraction = {...snapshot.extracao, permite_envio_validacao:true, bloqueia_calculo:true,
      pendencias:[{tipo:'CORRESPONDENCIA_CONCESSIONARIA', mensagem:'Concessionária sem correspondência cadastral', bloqueia_envio_validacao:false, bloqueia_calculo:true}]};
    const result = {...snapshot, extracao:extraction};
    let calculations=0, sends=0, processing=0, associations=0;
    const auth = {usuario:{id_usuario:1,nome:'Operador',matricula:'DEMO',funcao:'maker'},prefixos:[{id_prefixo:1,codigo_prefixo:'REF',nome:'Unidade'}],id_prefixo_ativo:1,id_prefixo_principal:1,expira_em:'2099-01-01'};
    await page.route('**/api/v1/**', async route => {
      const request=route.request(), path=new URL(request.url()).pathname.replace('/api/v1/','');
      let data=[];
      if(path==='auth/sessao' || path==='auth/login') data=auth;
      else if(path==='documentos/upload') data=result.documento;
      else if(path.endsWith('/processar-inteligente')) { processing++; data=result; }
      else if(path.endsWith('/revalidar')) data=extraction;
      else if(path.endsWith('/enviar-validacao')) { sends++; extraction.situacao_validacao='revisao_cadastral_pendente'; data=extraction; }
      else if(path==='concessionarias/elegiveis/associacao') data=[{id_concessionaria:9,nome:'Cadastro demonstrativo escolhido pelo revisor',ativo:true}];
      else if(path.endsWith('/resolver-concessionaria')) {
        associations++; assert.deepEqual(request.postDataJSON(),{id_concessionaria:9});
        if(associations===1) return route.fulfill({status:403,json:{detail:'Associação recusada no teste'}});
        extraction.situacao_validacao='validada'; extraction.resultado_validacao_documental='VALIDO'; extraction.bloqueia_calculo=false; extraction.pendencias=[];
        extraction.evidencias_validacao_documental={nome_concessionaria:'Cadastro demonstrativo escolhido pelo revisor',id_concessionaria:9};
        result.documento.id_conta=21; data=extraction;
      }
      else if(path==='extracoes_inteligentes') data=[extraction];
      else if(path==='documentos') data=[result.documento];
      else if(path.startsWith('dados_extraidos/') && path.endsWith('/validacao')) {
        const field=result.campos_encontrados.find(f=>f.id_dado_extraido===Number(path.split('/')[1]));
        data={...field,valor_validado:request.postDataJSON().valor_validado,situacao_validacao:'validada'};
      } else if(path.startsWith('itens_extraidos/') && path.endsWith('/validacao')) data=result.itens_encontrados.find(f=>f.id_item_extraido===Number(path.split('/')[1]));
      else if(path.endsWith('/calcular')) {calculations++;data={id_calculo:5,id_conta:21,data_calculo:'2026-11-02T12:00:00',valor_calculado:'736.53',situacao:'validado'};}
      await route.fulfill({json:data});
    });
    await page.goto(process.env.REVIEW_URL || 'http://127.0.0.1:5173');
    await page.locator('input[type=file]').setInputFiles({name:'referencia.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jfWQAAAAASUVORK5CYII=', 'base64')});
    await page.getByRole('button',{name:'Iniciar processamento'}).click();
    const button=page.getByRole('button',{name:'Enviar para validação'});
    await button.waitFor();
    assert.equal(await button.isEnabled(),true);
    const alert=page.locator('.documentary-alert-review').first();
    assert.equal(await alert.evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(254, 242, 242)');
    await page.screenshot({path:'/tmp/bb-revisao-cadastral-antes.png',fullPage:true});
    await button.click();
    await page.getByText('Documento enviado para validação',{exact:true}).waitFor();
    assert.equal(sends,1); assert.equal(calculations,0);
    await page.screenshot({path:'/tmp/bb-revisao-cadastral-enviada.png',fullPage:true});
    assert.equal(await page.locator('.stepper [aria-current="step"]').innerText(),'3\nValidação');
    await page.getByRole('button',{name:'Associar concessionária',exact:true}).click();
    await page.getByRole('dialog').waitFor();
    await page.getByLabel('Associar a:').selectOption('9');
    await page.getByRole('button',{name:'Confirmar associação'}).click();
    await page.getByRole('dialog').getByRole('alert').waitFor();
    assert.equal(await page.getByLabel('Associar a:').inputValue(),'9');
    await page.screenshot({path:'/tmp/bb-alias-modal.png',fullPage:true});
    await page.getByRole('button',{name:'Confirmar associação'}).click();
    await page.getByText('Correspondência cadastral resolvida',{exact:true}).waitFor();
    assert.equal(await page.getByRole('dialog').count(),0);
    assert.equal(processing,1); assert.equal(calculations,0);
    assert.ok(await page.getByText(nome,{exact:true}).count());
    assert.equal(await page.locator('.stepper [aria-current="step"]').innerText(),'3\nValidação');
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:'/tmp/bb-alias-mobile.png',fullPage:true});
    await page.getByRole('button',{name:'Calcular fatura'}).click();
    await page.getByText('Fatura processada com sucesso!',{exact:true}).waitFor();
    assert.equal(calculations,1); assert.equal(processing,1);
    console.log('Navegador: etapa 3, modal, listagem, ID, erro recuperável, sucesso, sem nova IA/cálculo, etapa 4 apenas após cálculo: aprovados.');
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
