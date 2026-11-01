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
