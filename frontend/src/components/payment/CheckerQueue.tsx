import { useState } from 'react';
import { api } from '../../api';
import { errorMessage } from '../../api/client';
import { useResource } from '../ui';
import { DocumentaryAlerts } from './DocumentaryAlerts';
import { CalculationSummary, DocumentPreview, labels } from './InvoiceSummary';
import type { JornadaPersistida } from '../../types';

function CheckerInvoice({ journey, reload }: { journey: JornadaPersistida; reload: () => void }) {
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
  return <article className="card"><h3>Fatura #{result.documento.id_documento} · {result.extracao.situacao_validacao}</h3>
    <DocumentPreview documentId={result.documento.id_documento} documentFormat={result.documento.formato} />
    <table><thead><tr><th>Campo</th><th>Extraído</th><th>Confirmado / corrigido</th></tr></thead><tbody>
      {result.campos_encontrados.map(f => <tr key={f.id_dado_extraido}><td>{labels[f.campo_identificado] ?? f.campo_identificado}</td><td>{f.valor_extraido}</td><td>{f.valor_validado}</td></tr>)}
      {result.itens_encontrados.map(i => <tr key={`i${i.id_item_extraido}`}><td>{i.tipo_normalizado}</td><td>{String(i.valor)}</td><td>{String(i.valor_validado ?? '')}</td></tr>)}
    </tbody></table>
    <CalculationSummary calculo={journey.calculo} /><DocumentaryAlerts extracao={result.extracao} confirmado />
    {result.extracao.situacao_validacao === 'processamento_concluido' ? <><label>Observação<input value={observacao} onChange={e => setObservacao(e.target.value)} disabled={busy} /></label>
      <div className="actions"><button className="primary" disabled={busy} onClick={() => void decide('aprovado')}>Confirmar fatura</button>
      <button disabled={busy} onClick={() => void decide('rejeitado')}>Rejeitar fatura</button></div></> : <p>Decisão final registrada.</p>}
    {result.extracao.historico_validacao_documental?.filter(h => h.evento === 'DECISAO_CHECKER').map((h, i) => <p key={i}>Decisão: {String(h.decisao)} · Usuário #{String(h.id_usuario)} · {String(h.data)} · {String(h.observacao)}</p>)}
    {error && <p role="alert">{error}</p>}
  </article>;
}
export function CheckerQueue() {
  const r = useResource(api.filaChecker);
  return <section><h2>Checker — faturas processadas</h2><button onClick={r.reload}>Atualizar faturas</button>
    {r.loading && <p role="status">Carregando faturas…</p>}{r.error && <p role="alert">{r.error}</p>}
    {r.data?.map(j => <CheckerInvoice key={j.documento?.id_documento} journey={j} reload={r.reload} />)}
    {r.data?.length === 0 && <p>Nenhuma fatura processada disponível neste prefixo.</p>}
  </section>;
}
