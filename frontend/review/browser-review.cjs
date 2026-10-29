// Revisão visual com contratos simulados; não substitui integração com PostgreSQL.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const path = require('node:path');
(async () => {
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({viewport:{width:1366,height:768}});
 const errors=[]; page.on('pageerror', e=>errors.push(String(e)));
 const account={id_conta:1,categoria:'energia',competencia:'2026-10',data_vencimento:'2026-11-10',valor_original:'276.34',situacao:'pendente',id_prefixo:1,id_concessionaria:1,numero_conta:'1234567'};
 const fields=[['valor_original','276.34'],['competencia','2026-10'],['data_vencimento','2026-11-10'],['codigo_barras','83620000002776340048100000000000000000000000'],['consumo','245']].map(([campo_identificado,valor_extraido],i)=>({id_dado_extraido:i+1,campo_identificado,valor_extraido,valor_validado:null,situacao_validacao:'pendente',id_extracao:1}));
 const calculation={id_calculo:12,id_conta:1,valor_inicial:'276.34',valor_calculado:'276.34',data_calculo:'2026-10-29T15:00:00',situacao:'validado',memoria_calculo:null};
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(), url=new URL(req.url()), p=url.pathname.replace('/api/v1/',''); let data=[];
  if(p==='contas_consumo') data=[account];
  else if(p==='prefixos') data=[{id_prefixo:1,codigo_prefixo:'9090',nome:'Agência demonstrativa'}];
  else if(p==='concessionarias') data=[{id_concessionaria:1,nome_fantasia:'Energia demonstrativa',razao_social:'Energia demonstrativa'}];
  else if(p.endsWith('/upload')) data={id_documento:1,id_conta:1};
  else if(p.endsWith('/processar')) { await new Promise(r=>setTimeout(r,1600)); data={campos_encontrados:fields,itens_encontrados:[],situacao:'processado'}; }
  else if(p.includes('/validacao')) { const id=Number(p.split('/')[1]); data={...fields[id-1],...req.postDataJSON(),situacao_validacao:'validada'}; fields[id-1]=data; }
  else if(p.endsWith('/calcular')) data={...calculation,valor_inicial:fields[0].valor_validado,valor_calculado:fields[0].valor_validado};
  await route.fulfill({json:data});
 });
 const out=path.join(__dirname,'screenshots');
 async function shot(name){await page.screenshot({path:path.join(out,name+'.png')}); if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw Error('Overflow: '+name);}
 await page.goto('http://127.0.0.1:5173'); await shot('01-login');
 await page.getByRole('button',{name:'Entrar',exact:true}).click();await shot('02-upload');
 await page.locator('input[type=file]').setInputFiles({name:'fatura.png',mimeType:'image/png',buffer:Buffer.from('image')});await page.getByText('Imagem selecionada.',{exact:false}).waitFor();
 await page.locator('input[type=file]').setInputFiles({name:'fatura.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\n%%EOF')});
 await page.getByLabel('Conta de referência').selectOption('1');
 await page.getByRole('button',{name:'Iniciar processamento'}).click();await page.getByRole('heading',{name:'Lendo e interpretando sua fatura...'}).waitFor();await shot('03-processamento');
 await page.getByRole('button',{name:'Editar dados'}).waitFor();await shot('04-resumo');
 await page.getByRole('button',{name:'Editar dados'}).click();await shot('05-edicao');
 await page.getByRole('dialog').getByLabel('Valor da fatura',{exact:false}).fill('280.00');
 await page.getByRole('button',{name:'Salvar alterações'}).click();await page.getByRole('dialog').waitFor({state:'detached'});
 await page.getByRole('button',{name:'Enviar para validação'}).click();await page.getByRole('heading',{name:'Dados prontos para validação'}).waitFor();await shot('06-validacao');
 await page.getByRole('button',{name:'Confirmar e continuar'}).click();await shot('07-confirmacao');
 await page.getByRole('link',{name:'Faturas',exact:true}).click();await page.getByRole('cell',{name:'276,34',exact:false}).waitFor();await shot('08-faturas');
 await page.getByRole('link',{name:'Relatórios',exact:true}).click();await shot('09-relatorios');
 for(const width of [375,768,1440,1920]){await page.setViewportSize({width,height:900});await page.getByRole('link',{name:'Pagamentos',exact:true}).click();if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow '+width);}
 if(errors.length)throw Error(errors.join('\n'));console.log('9 capturas; jornada, edição, imagem e responsividade verificadas com API simulada.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
