import { useState } from 'react';
import { api } from '../../api';
import { errorMessage } from '../../api/client';
import { money, useResource } from '../ui';
import { formatCompetenciaDisplay } from '../../utils/competencia';
import { DocumentaryAlerts } from './DocumentaryAlerts';
import { CalculationSummary, DocumentPreview, labels } from './InvoiceSummary';
import type { JornadaPersistida } from '../../types';

export function checkerStatus(journey: JornadaPersistida) {
  switch (journey.processamento?.extracao.situacao_validacao) {
    case 'confirmada_checker': return { label: 'Aprovado', tone: 'approved' };
    case 'rejeitada_checker': return { label: 'Rejeitado', tone: 'rejected' };
    default: return { label: 'Pendente', tone: 'pending' };
  }
}
export function toggleCheckerCard(current: number | null, id: number) { return current === id ? null : id; }
function calculationTime(value: string) {
  return new Date(value + (/Z$|[+-]\d{2}:\d{2}$/.test(value) ? '' : 'Z')).getTime();
}
export function sortCheckerQueue(journeys: JornadaPersistida[]) {
  return journeys.filter(j => j.processamento && j.calculo).slice().sort((a, b) => calculationTime(b.calculo!.data_calculo) - calculationTime(a.calculo!.data_calculo));
}
export function CheckerInvoice({ journey, reload, expanded, onToggle }: { journey: JornadaPersistida; reload: () => void; expanded: boolean; onToggle: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [observacao, setObservacao] = useState('');
  const result = journey.processamento;
  if (!result || !journey.calculo) return null;
  async function decide(decisao: 'aprovado' | 'rejeitado') {
    if (!result) return;
    setBusy(true); setError('');
    try { await api.decidirDocumento(result.documento.id_documento, decisao, observacao); reload(); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  const status = checkerStatus(journey);
  const id = result.documento.id_documento;
  const field = (...names: string[]) => {
    const found = names.map(name => result.campos_encontrados.find(f => f.campo_identificado === name)).find(Boolean);
    return found?.valor_validado ?? found?.valor_normalizado ?? found?.valor_extraido ?? 'Não informado';
  };
  const maker = result.extracao.historico_validacao_documental?.slice().reverse().find(h => h.evento === 'CALCULO_DEMO');
  const type = field('categoria', 'tipo_servico', 'tipo_documento');
  const fields = [
    ['Tipo da conta', ({CONTA_ENERGIA:'Energia', CONTA_AGUA:'Água', energia:'Energia', agua:'Água'} as Record<string,string>)[type] ?? type],
    ['Concessionária', field('concessionaria', 'nome_concessionaria')],
    ['Competência', formatCompetenciaDisplay(field('competencia'))],
    ['Prefixo / unidade', `${field('prefixo', 'agencia')} / ${field('unidade_consumidora', 'unidade_consumo', 'numero_conta')}`],
    ['Valor original', money(journey.calculo.valor_inicial)],
    ['Valor calculado', money(journey.calculo.valor_calculado)],
    ['Diferença', journey.calculo.memoria_calculo?.diferenca !== undefined ? money(journey.calculo.memoria_calculo.diferenca) : 'Não informada'],
    ['Usuário maker', maker?.id_usuario != null ? `Maker #${String(maker.id_usuario)}` : 'Não informado'],
    ['Data/hora', new Date(calculationTime(journey.calculo.data_calculo)).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })],
  ];
  return <article className="card checker-card">
    <button type="button" className="checker-toggle" aria-expanded={expanded} aria-controls={`checker-details-${id}`} id={`checker-toggle-${id}`} onClick={onToggle}>
      <span className="checker-card-top">
        <span className={`checker-status ${status.tone}`}>{status.label}</span>
        {fields.slice(0, 3).map(([label, value]) => <strong className="checker-heading-field" key={label} title={label}>{value}</strong>)}
        <span className="checker-action">{expanded ? 'Recolher' : status.tone === 'pending' ? 'Analisar' : 'Ver detalhes'}</span>
      </span>
      <span className="checker-fields">{fields.slice(3).map(([label, value]) => <span key={label}><span className="checker-label">{label}: </span><strong>{value}</strong></span>)}</span>
    </button>
    {expanded && <div className="checker-details" id={`checker-details-${id}`} role="region" aria-labelledby={`checker-toggle-${id}`}>
    <DocumentPreview documentId={result.documento.id_documento} documentFormat={result.documento.formato} />
    <h3>Dados completos extraídos</h3><div className="table-wrap"><table><thead><tr><th>Campo</th><th>Extraído</th><th>Confirmado / corrigido</th></tr></thead><tbody>
      {result.campos_encontrados.map(f => <tr key={f.id_dado_extraido}><td>{labels[f.campo_identificado] ?? f.campo_identificado}</td><td>{f.valor_extraido}</td><td>{f.valor_validado}</td></tr>)}
      {result.itens_encontrados.map(i => <tr key={`i${i.id_item_extraido}`}><td>{i.tipo_normalizado}</td><td>{String(i.valor)}</td><td>{String(i.valor_validado ?? '')}</td></tr>)}
    </tbody></table></div>
    <CalculationSummary calculo={journey.calculo} /><DocumentaryAlerts extracao={result.extracao} confirmado />
    {result.extracao.situacao_validacao === 'processamento_concluido' ? <><label>Observação<input value={observacao} onChange={e => setObservacao(e.target.value)} disabled={busy} /></label>
      <div className="actions"><button className="primary" disabled={busy} onClick={() => void decide('aprovado')}>Confirmar fatura</button>
      <button disabled={busy} onClick={() => void decide('rejeitado')}>Rejeitar fatura</button></div></> : <p>Decisão final registrada.</p>}
    {result.extracao.historico_validacao_documental?.filter(h => h.evento === 'DECISAO_CHECKER').map((h, i) => <p key={i}>Decisão: {String(h.decisao)} · Usuário #{String(h.id_usuario)} · {String(h.data)} · {String(h.observacao)}</p>)}
    {busy && <p role="status">Registrando decisão…</p>}
    {error && <p role="alert">{error}</p>}
    </div>}
  </article>;
}
export function CheckerQueue() {
  const r = useResource(api.filaChecker);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  return <section><h2>Checker — faturas processadas</h2><button onClick={r.reload}>Atualizar faturas</button>
    {r.loading && <p role="status">Carregando faturas…</p>}{r.error && <p role="alert">{r.error}</p>}
    {r.data && sortCheckerQueue(r.data).map(j => {
      const id = j.processamento!.documento.id_documento;
      return <CheckerInvoice key={id} journey={j} reload={r.reload} expanded={expandedId === id} onToggle={() => setExpandedId(current => toggleCheckerCard(current, id))} />;
    })}
    {r.data?.length === 0 && <p>Nenhuma fatura processada disponível neste prefixo.</p>}
  </section>;
}
