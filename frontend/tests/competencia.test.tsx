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
  resultado_validacao_documental:'EVIDENCIA_INSUFICIENTE', permite_envio_validacao:true, bloqueia_calculo:true,
  pendencias:[{tipo:'CORRESPONDENCIA_CONCESSIONARIA', mensagem:'Concessionária sem correspondência cadastral', bloqueia_envio_validacao:false, bloqueia_calculo:true}],
} satisfies ExtracaoInteligente;
test('pendência cadastral usa mensagem específica e alerta review', () => {
  const html = renderToStaticMarkup(<DocumentaryAlerts extracao={review} concessionaria="COMPANHIA ENERGÉTICA DE PERNAMBUCO" />);
  for (const text of ['documentary-alert-review','Pendência encontrada','Concessionária sem correspondência cadastral','COMPANHIA ENERGÉTICA DE PERNAMBUCO','A fatura pode ser enviada para revisão cadastral.']) assert.ok(html.includes(text));
  assert.equal(canSubmitReview(review), true);
});
test('envio obedece contrato estruturado sem interpretar texto livre', () => {
  for (const resultado of ['DOCUMENTO_NAO_SUPORTADO','REGIAO_NAO_SUPORTADA','EVIDENCIA_INSUFICIENTE']) assert.equal(canSubmitReview({...review, resultado_validacao_documental:resultado, permite_envio_validacao:false}), false);
  assert.equal(canSubmitReview({...review, permite_envio_validacao:undefined}), false);
  assert.equal(canSubmitReview({...review, motivo_validacao_documental:'Texto arbitrário'}), true);
});
test('múltiplas pendências aparecem separadamente', () => {
  const html = renderToStaticMarkup(<DocumentaryAlerts extracao={{...review, pendencias:[...review.pendencias,{tipo:'CAMPO_OBRIGATORIO', mensagem:'Unidade consumidora ausente', bloqueia_envio_validacao:true, bloqueia_calculo:true}]}} />);
  assert.equal((html.match(/documentary-alert-review/g) ?? []).length, 2);
  assert.ok(html.includes('Unidade consumidora ausente'));
});
test('alertas oferecem quatro variantes centralizadas', () => {
  for (const variant of ['info','warning','review','error'] as const) assert.ok(renderToStaticMarkup(<Alert variant={variant}>Mensagem</Alert>).includes(`documentary-alert-${variant}`));
});
