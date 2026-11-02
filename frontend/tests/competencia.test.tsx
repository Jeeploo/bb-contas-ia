import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { formatCompetenciaDisplay, parseCompetenciaDisplay } from '../src/utils/competencia';
import { InvoiceSummary } from '../src/components/payment/InvoiceSummary';

test('competência canônica e apresentação não alteram o original', () => {
  const original = '2026-09';
  assert.equal(formatCompetenciaDisplay(original), '09/2026');
  assert.equal(parseCompetenciaDisplay('09/2026'), original);
  assert.equal(parseCompetenciaDisplay(original), original);
  for (const value of ['13/2026', '2026-00', '09/26', '']) assert.throws(() => parseCompetenciaDisplay(value));
});
test('resumo apresenta valor, competência e identificadores mascarados', () => {
  const html = renderToStaticMarkup(<InvoiceSummary fields={[
    { label:'Valor da fatura', value:'R$ 736,53' },
    { label:'Competência', value:'2026-09' },
    { label:'Concessionária', value:'Companhia Energética de Pernambuco' },
    { label:'Unidade consumidora', value:'1234-78' },
    { label:'Código de barras', value:'8'.repeat(48) },
    { label:'Consumo', value:'523 kWh' },
  ]} />);
  for (const value of ['736,53', '09/2026', 'Companhia Energética de Pernambuco', '***4-78', '***8888', '523 kWh']) assert.ok(html.includes(value), value);
  assert.ok(!html.includes('Fictícia'));
  assert.ok(!html.includes('1234-78'));
  assert.ok(!html.includes('Aguardando revisão'));
});

// URL pública é injetada exclusivamente por configuração de build.
import { apiBase } from '../src/api/config';
test('API URL explícita, HTTPS e ausência de fallback local', () => {
  assert.equal(apiBase('https://api.exemplo.com'), 'https://api.exemplo.com/api/v1');
  assert.equal(apiBase('http://127.0.0.1:8000/'), 'http://127.0.0.1:8000/api/v1');
  for (const value of [undefined, '', '/api', 'ftp://api.exemplo.com', 'https://user:pass@api.exemplo.com', 'https://api.exemplo.com/api/v1']) assert.throws(() => apiBase(value));
});

import { DocumentaryAlerts, canSubmitReview, Alert } from '../src/components/payment/DocumentaryAlerts';
import type { ExtracaoInteligente } from '../src/types';
const review = { id_extracao:1, data_processamento:'', nivel_confianca:null, situacao_validacao:'pendente', id_documento:1,
  resultado_validacao_documental:'EVIDENCIA_INSUFICIENTE', permite_envio_validacao:true, bloqueia_calculo:false,
  pendencias:[{tipo:'CORRESPONDENCIA_CONCESSIONARIA', mensagem:'Concessionária sem correspondência cadastral', bloqueia_envio_validacao:false, bloqueia_calculo:false}],
} satisfies ExtracaoInteligente;
test('pendência cadastral usa mensagem específica e alerta amarelo não bloqueante', () => {
  const html = renderToStaticMarkup(<DocumentaryAlerts extracao={review} concessionaria="COMPANHIA ENERGÉTICA DE PERNAMBUCO" />);
  for (const text of ['documentary-alert-warning','Pendências e alertas','Concessionária sem correspondência cadastral','COMPANHIA ENERGÉTICA DE PERNAMBUCO','Pendência que não impede continuar.']) assert.ok(html.includes(text));
  assert.equal(canSubmitReview(review), true);
});
test('envio obedece contrato estruturado sem interpretar texto livre', () => {
  for (const resultado of ['DOCUMENTO_NAO_SUPORTADO','REGIAO_NAO_SUPORTADA','EVIDENCIA_INSUFICIENTE']) assert.equal(canSubmitReview({...review, resultado_validacao_documental:resultado, permite_envio_validacao:false}), false);
  assert.equal(canSubmitReview({...review, permite_envio_validacao:undefined}), false);
  assert.equal(canSubmitReview({...review, motivo_validacao_documental:'Texto arbitrário'}), true);
});
test('múltiplas pendências aparecem separadamente', () => {
  const html = renderToStaticMarkup(<DocumentaryAlerts extracao={{...review, pendencias:[...review.pendencias,{tipo:'CAMPO_OBRIGATORIO', mensagem:'Unidade consumidora ausente', bloqueia_envio_validacao:true, bloqueia_calculo:true}]}} />);
  assert.equal((html.match(/documentary-alert-warning/g) ?? []).length, 1);
  assert.equal((html.match(/documentary-alert-error/g) ?? []).length, 1);
  assert.ok(html.includes('Unidade consumidora ausente'));
});
test('alertas oferecem quatro variantes centralizadas', () => {
  for (const variant of ['info','warning','review','error'] as const) assert.ok(renderToStaticMarkup(<Alert variant={variant}>Mensagem</Alert>).includes(`documentary-alert-${variant}`));
});

import { journeyStep } from '../src/utils/journey';
import { PaymentStepper } from '../src/components/payment/PaymentStepper';
import { ConcessionariaReview, AssociarConcessionariaModal } from '../src/components/payment/ConcessionariaReview';
test('envio e revisão cadastral permanecem na etapa 3 sem conclusão visual', () => {
  assert.equal(journeyStep(),1);
  assert.equal(journeyStep(review),2);
  const sent = {...review, historico_validacao_documental:[{evento:'ENVIADO_PARA_VALIDACAO'}]};
  assert.equal(journeyStep(sent),3);
  assert.equal(journeyStep({...sent,situacao_validacao:'revisao_cadastral_pendente'}),3);
  const html=renderToStaticMarkup(<PaymentStepper step={journeyStep(sent)} />);
  assert.ok(html.includes('aria-current="step"><span>3</span>'));
  assert.ok(!html.includes('aria-current="step"><span>4</span>'));
});
test('validação exibe nome extraído e ação de associação', () => {
  const html=renderToStaticMarkup(<ConcessionariaReview extracao={review} nome="COMPANHIA ENERGÉTICA DE PERNAMBUCO" busy={false} onAssociate={()=>{}} onCalculate={()=>{}} />);
  for (const text of ['Documento enviado para validação','Pendência cadastral','Associar concessionária','COMPANHIA ENERGÉTICA DE PERNAMBUCO']) assert.ok(html.includes(text));
  assert.ok(html.includes('Calcular fatura'));
  assert.ok(html.includes('(opcional)'));
});
test('modal lista cadastros e preserva nome extraído', () => {
  const html=renderToStaticMarkup(<AssociarConcessionariaModal nome="COMPANHIA ENERGÉTICA DE PERNAMBUCO" opcoes={[{id_concessionaria:7,nome:'Cadastro oficial',ativo:true}]} selected={7} busy={false} error="" onSelect={()=>{}} onClose={()=>{}} onConfirm={()=>{}} />);
  for (const text of ['dialog','COMPANHIA ENERGÉTICA DE PERNAMBUCO','value="7"','Cadastro oficial','Confirmar associação','Cancelar']) assert.ok(html.includes(text));
});
test('sucesso exibe cadastro resolvido e cálculo depende de elegibilidade', () => {
  const resolved={...review,situacao_validacao:'validada',pendencias:[],bloqueia_calculo:false,evidencias_validacao_documental:{nome_concessionaria:'Cadastro oficial'}};
  assert.equal(journeyStep(resolved),3);
  const html=renderToStaticMarkup(<ConcessionariaReview extracao={resolved} nome="Nome original" busy={false} onAssociate={()=>{}} onCalculate={()=>{}} />);
  for (const text of ['Dados documentais disponíveis','Cadastro oficial','Nome original','Calcular fatura']) assert.ok(html.includes(text));
  assert.ok(!html.includes('Associar concessionária'));
});

import { advanceProcessingProgress, processingActivityState, processingActivities, type ProcessingPhase } from '../src/utils/processingProgress';
import { ProcessingState } from '../src/components/payment/ProcessingState';
test('progresso estimado respeita fronteiras HTTP e nunca atinge 100 antes do sucesso', () => {
  let progress = 0;
  for (const [phase, ceiling] of [['uploading',16],['extracting',78],['validating',94]] as const) {
    for (let tick=0; tick<1000; tick++) {
      const next=advanceProcessingProgress(progress,phase);
      assert.ok(next>=progress && next<=ceiling);
      progress=next;
    }
    assert.equal(progress,ceiling);
    assert.ok(progress<100);
  }
  for (let tick=0; tick<100; tick++) progress=advanceProcessingProgress(progress,'complete');
  assert.equal(progress,100);
});
test('fases visuais avançam, concluem no sucesso e param no erro', () => {
  for (const [index,progress] of [0,18,38,58,80,95].entries()) {
    for (let i=0; i<processingActivities.length; i++) {
      assert.equal(processingActivityState(i,progress,'extracting'),i<index?'complete':i===index?'active':'pending');
    }
  }
  for (let i=0; i<6; i++) assert.equal(processingActivityState(i,100,'complete'),'complete');
  assert.equal(advanceProcessingProgress(62,'error'),62);
  assert.equal(processingActivityState(3,62,'error'),'error');
});
test('tela inicia em zero com progresso acessível e erro permite nova tentativa', () => {
  for (const phase of ['uploading','error'] as ProcessingPhase[]) {
    const html=renderToStaticMarkup(<ProcessingState phase={phase} error="Falha temporária. Tente novamente." onComplete={()=>{}} onRetry={()=>{}} onBack={()=>{}} />);
    assert.ok(html.includes('role="progressbar"'));
    assert.ok(html.includes('aria-valuenow="0"'));
    assert.ok(!html.includes('class="loader"'));
    for (const activity of processingActivities) assert.ok(html.includes(activity));
    if(phase==='error') for (const value of ['role="alert"','Falha temporária','Tentar novamente','Escolher outro arquivo']) assert.ok(html.includes(value));
  }
});

test('erro após upload mantém documento recebido concluído', () => {
  const html=renderToStaticMarkup(<ProcessingState phase="error" received error="Leitura indisponível" onComplete={()=>{}} onRetry={()=>{}} onBack={()=>{}} />);
  assert.ok(html.includes('class="processing-activity complete"'));
  assert.ok(html.includes('Documento recebido<span class="sr-only"> — concluída'));
  assert.ok(html.includes('Extraindo informações<span class="sr-only"> — interrompida'));
});

import { CalculationSummary, ConfirmationCard } from '../src/components/payment/InvoiceSummary';
import type { Calculo } from '../src/types';
const calculation = {id_calculo:1,id_conta:1,id_regra:1,data_calculo:'2026-11-02T12:00:00Z',situacao:'validado',valor_inicial:'100.00',valor_calculado:'90.00',memoria_calculo:{estrategia:'COEFICIENTE',valor_base:'100.00',resultado:'90.00',diferenca:'-10.00',parametros:{coeficiente:'1.111111'},componentes_considerados:[],componentes_ignorados:[],resultado_sem_arredondamento:'90',id_perfil:1,id_regra:1,versao_regra:'1',id_extracao:1,competencia:'2026-09'}} satisfies Calculo;
test('stepper reconstrói resumo, validação e conclusão a partir do backend', () => {
  assert.equal(journeyStep(review), 2);
  assert.equal(journeyStep({...review,situacao_validacao:'validada'}), 3);
  assert.equal(journeyStep({...review,situacao_validacao:'processamento_concluido'}, calculation), 4);
  assert.equal(journeyStep({...review,situacao_validacao:'revisao_cadastral_pendente'}, calculation), 4);
  assert.notEqual(journeyStep({...review,bloqueia_calculo:true}, calculation), 4);
});
test('resultado mostra base, diferença, regra e memória, e conclusão oferece Nova fatura', () => {
  const summary=renderToStaticMarkup(<CalculationSummary calculo={calculation} />);
  for (const text of ['100,00','90,00','Diferença:','10,00','COEFICIENTE','1.111111','Ver detalhes do cálculo']) assert.ok(summary.includes(text),text);
  const html=renderToStaticMarkup(<ConfirmationCard fields={[]} calculo={calculation} onReset={()=>{}} />);
  for (const text of ['Processamento concluído','Checker','Nova fatura']) assert.ok(html.includes(text));
});
test('unidade sem vínculo preserva dados e permite continuar', () => {
  const e={...review,pendencias:[{tipo:'VINCULO_UNIDADE',mensagem:'Unidade consumidora sem vínculo cadastral ativo.',bloqueia_envio_validacao:false,bloqueia_calculo:false}]};
  assert.equal(canSubmitReview(e),true);
  const html=renderToStaticMarkup(<DocumentaryAlerts extracao={e} />);
  for (const text of ['documentary-alert-warning','A informação foi preservada','Pendência que não impede continuar.']) assert.ok(html.includes(text));
  assert.ok(!html.includes('documentary-alert-error'));
});

test('regra DEMO apresenta divisão, coeficiente, diferença e aviso de escopo específico', () => {
  const demo={...calculation,valor_inicial:'736.53',valor_calculado:'813.40',memoria_calculo:{...calculation.memoria_calculo,valor_base:'736.53',resultado:'813.40',diferenca:'76.87',parametros:{coeficiente:'0.9055'},coeficiente:'0.9055',operacao:'DIVISAO',expressao:'736.53 / 0.9055',nome_regra:'Regra DEMO — Coeficiente 0,9055',demonstrativa:true,aviso_demo:'Regra demonstrativa baseada em um caso real de prefixo específico. Não representa uma regra financeira aplicável a todos os prefixos do Banco do Brasil.'}};
  const html=renderToStaticMarkup(<CalculationSummary calculo={demo} />);
  for (const text of ['736,53','813,40','76,87','Regra DEMO — Coeficiente 0,9055','Coeficiente: 0,9055',' / ','Operação aplicada:','Não representa uma regra financeira aplicável a todos os prefixos do Banco do Brasil.']) assert.ok(html.includes(text),text);
});

test('fallback DEMO sem cadastro exibe aviso e cálculo sem erro de perfil', () => {
  const demo = {...calculation, id_calculo: undefined, id_conta: null, id_regra: null,
    id_extracao: 15, origem: 'documental_demo' as const, valor_inicial:'736.53',valor_calculado:'813.40',
    memoria_calculo:{...calculation.memoria_calculo,id_regra:null,id_perfil:null,
      nome_regra:'Regra DEMO — Coeficiente 0,9055',demonstrativa:true,fallback_demo:true,
      aviso_demo:'Baseada em caso real de prefixo específico; não representa regra aplicável a todos os prefixos.',
      coeficiente:'0.9055',operacao:'DIVISAO',diferenca:'76.87'}};
  const html=renderToStaticMarkup(<CalculationSummary calculo={demo} />);
  for (const text of ['736,53','813,40','76,87','Regra demonstrativa aplicada ao cálculo.', 'Baseada em caso real']) assert.ok(html.includes(text),text);
  assert.ok(!html.includes('Prefixo deve ter exatamente'));
  assert.equal(journeyStep({...review,situacao_validacao:'validada'}, undefined),3);
});
