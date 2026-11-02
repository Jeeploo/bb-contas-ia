// PLAYWRIGHT_MODULE=/path/to/playwright REVIEW_SNAPSHOT=/tmp/bb-real-response.json node review/review-cadastral.cjs
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const snapshot = JSON.parse(fs.readFileSync(process.env.REVIEW_SNAPSHOT, 'utf8'));
  const browser = await chromium.launch({ headless:true });
  try {
    const page = await browser.newPage({ viewport:{width:1440,height:1100} });
    const extraction = {...snapshot.extracao, permite_envio_validacao:true, bloqueia_calculo:true,
      pendencias:[{tipo:'CORRESPONDENCIA_CONCESSIONARIA', mensagem:'Concessionária sem correspondência cadastral', bloqueia_envio_validacao:false, bloqueia_calculo:true}]};
    const result = {...snapshot, extracao:extraction};
    let calculations=0, sends=0;
    const auth = {usuario:{id_usuario:1,nome:'Operador',matricula:'DEMO',funcao:'maker'},prefixos:[{id_prefixo:1,codigo_prefixo:'REF',nome:'Unidade'}],id_prefixo_ativo:1,id_prefixo_principal:1,expira_em:'2099-01-01'};
    await page.route('**/api/v1/**', async route => {
      const request=route.request(), path=new URL(request.url()).pathname.replace('/api/v1/','');
      let data=[];
      if(path==='auth/sessao' || path==='auth/login') data=auth;
      else if(path==='documentos/upload') data=result.documento;
      else if(path.endsWith('/processar-inteligente')) data=result;
      else if(path.endsWith('/revalidar')) data=extraction;
      else if(path.endsWith('/enviar-validacao')) { sends++; extraction.situacao_validacao='revisao_cadastral_pendente'; data=extraction; }
      else if(path==='extracoes_inteligentes') data=[extraction];
      else if(path==='documentos') data=[result.documento];
      else if(path.startsWith('dados_extraidos/') && path.endsWith('/validacao')) {
        const field=result.campos_encontrados.find(f=>f.id_dado_extraido===Number(path.split('/')[1]));
        data={...field,valor_validado:request.postDataJSON().valor_validado,situacao_validacao:'validada'};
      } else if(path.startsWith('itens_extraidos/') && path.endsWith('/validacao')) data=result.itens_encontrados.find(f=>f.id_item_extraido===Number(path.split('/')[1]));
      else if(path.endsWith('/calcular')) calculations++;
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
    for (const tipo of ['DOCUMENTO_NAO_SUPORTADO','REGIAO_NAO_SUPORTADA','CAMPO_OBRIGATORIO']) {
      extraction.situacao_validacao='pendente'; extraction.permite_envio_validacao=false;
      extraction.pendencias=[{tipo,mensagem:tipo,bloqueia_envio_validacao:true,bloqueia_calculo:true},
        {tipo:'CORRESPONDENCIA_CONCESSIONARIA',mensagem:'Concessionária sem correspondência cadastral',bloqueia_envio_validacao:false,bloqueia_calculo:true}];
      await page.reload();
      await page.locator('input[type=file]').setInputFiles({name:'referencia.png',mimeType:'image/png',buffer:Buffer.from('referencia')});
      await page.getByRole('button',{name:'Iniciar processamento'}).click();
      await button.waitFor(); assert.equal(await button.isEnabled(),false);
      assert.equal(await page.locator('.documentary-alert-review').count(),2);
    }
    console.log('Referência persistida: alerta review, botão habilitado, envio realizado, cálculo não chamado.');
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
