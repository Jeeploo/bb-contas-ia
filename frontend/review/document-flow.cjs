// PLAYWRIGHT_MODULE=/path/to/playwright node review/document-flow.cjs
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const multiple of [false, true]) {
      const page = await browser.newPage();
      const fields = Object.entries({ tipo_documento:'CONTA_ENERGIA', competencia:'09/2026', valor_original:'736,53', data_vencimento:'2026-10-20', concessionaria:'Companhia Energética de Pernambuco', unidade_consumidora:'1234-78', codigo_barras:'8'.repeat(48), consumo:'523', unidade_consumo:'kWh', municipio:'Paulista', uf:'PE' }).map(([campo_identificado, valor_extraido], i) => ({ id_dado_extraido:i+1, campo_identificado, valor_extraido, valor_normalizado:campo_identificado === 'competencia' ? '2026-09' : campo_identificado === 'valor_original' ? '736.53' : valor_extraido, valor_validado:null, situacao_validacao:'pendente' }));
      const documento = { id_documento:10, id_conta:null };
      const extracao = { id_extracao:20, resultado_validacao_documental:'VALIDO', evidencias_validacao_documental:{id_concessionaria:2} };
      let uploads=0, reads=0, validatedCompetencia, signedIn=false;
      const auth={usuario:{id_usuario:1,nome:'Operador',matricula:'DEMO-maker',funcao:'maker'},prefixos:[1,...(multiple?[2]:[])].map(id=>({id_prefixo:id,codigo_prefixo:id===1?'PAU-DEMO':'OUTRO',nome:'Paulista'})),id_prefixo_ativo:multiple?null:1,id_prefixo_principal:1,expira_em:'2099-01-01'};
      await page.route('**/api/v1/**', async route => {
        const req=route.request(), p=new URL(req.url()).pathname.replace('/api/v1/',''); let data=[];
        if(p==='auth/sessao') { if(!signedIn) return route.fulfill({status:401,json:{detail:'Sem sessão'}}); data=auth; }
        else if(p==='auth/login') { signedIn=true; data=auth; }
        else if(p==='auth/prefixo') { auth.id_prefixo_ativo=req.postDataJSON().id_prefixo; data=auth; }
        else if(p==='usuarios') data=[{id_usuario:1,nome:'Operador',situacao:'ativo'}];
        else if(p==='prefixos') data=[1,...(multiple ? [2] : [])].map(id=>({id_prefixo:id,codigo_prefixo:id===1?'PAU-DEMO':'OUTRO',nome:'Paulista',situacao:'ativo'}));
        else if(p==='usuarios/1/prefixos') data={vinculos:[{id_prefixo:1,ativo:true},...(multiple?[{id_prefixo:2,ativo:true}]:[])]};
        else if(p==='documentos/upload') { uploads++; assert.equal(new URL(req.url()).searchParams.has('id_usuario'),false); data={...documento}; }
        else if(p==='documentos/10/processar-inteligente') { reads++; documento.id_conta=30; data={documento,extracao,campos_encontrados:fields,itens_encontrados:[]}; }
        else if(p.startsWith('dados_extraidos/')) {
          const field=fields.find(f=>f.id_dado_extraido===Number(p.split('/')[1]));
          Object.assign(field, req.postDataJSON(), {situacao_validacao:'validada'}); data=field;
          if(field.campo_identificado==='competencia') validatedCompetencia=field.valor_validado;
        }
        else if(p==='extracoes_inteligentes') data=[extracao];
        else if(p==='documentos') data=[documento];
        else throw Error('Endpoint inesperado: '+p);
        await route.fulfill({json:data});
      });
      await page.goto(process.env.FRONTEND_URL || 'http://127.0.0.1:5173');
      await page.getByLabel('Matrícula',{exact:true}).fill('DEMO-maker');
      await page.getByLabel('Senha',{exact:true}).fill('senha-de-teste');
      await page.getByLabel('2º fator',{exact:true}).fill('123456');
      await page.getByRole('button',{name:'Entrar',exact:true}).click();
      await page.getByRole('heading',{name:'Pagamento de faturas'}).waitFor();
      await page.locator('input[type=file]').setInputFiles({name:'conta.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4')});
      const processButton=page.getByRole('button',{name:'Iniciar processamento'});
      if(multiple) {
        assert.equal(await processButton.isDisabled(),true);
        await page.getByLabel('Prefixo',{exact:true}).selectOption('1');
      }
      await processButton.click();
      await page.getByRole('heading',{name:'Resumo da fatura'}).waitFor();
      const summary=await page.locator('.invoice-fields').innerText();
      for(const value of ['736,53','09/2026','***4-78','***8888','523 kWh','Companhia Energética de Pernambuco','PAU-DEMO']) assert.ok(summary.includes(value),value);
      assert.ok(!summary.includes('Fictícia'));
      assert.ok(!summary.includes('Aguardando revisão'));
      await page.getByRole('button',{name:'Editar dados'}).click();
      const competencia=page.getByLabel('Competência',{exact:true});
      assert.equal(await competencia.inputValue(),'09/2026');
      await competencia.fill('09/2026');
      await page.getByRole('button',{name:'Salvar alterações'}).click();
      await page.locator('dialog').waitFor({state:'detached'});
      assert.equal(validatedCompetencia,'2026-09');
      assert.equal(fields.find(f=>f.campo_identificado==='competencia').valor_extraido,'09/2026');
      assert.equal(uploads,1);assert.equal(reads,1);
      await page.setViewportSize({width:390,height:844});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await page.close();
    }
    console.log('Jornada, prefixo único/múltiplos, resumo e edição canônica: OK');
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1});
