import { useSearchParams } from 'react-router-dom';
import { useState } from 'react';
import { api } from '../api';
import { useResource, money } from '../components/ui';
export function InvoiceHistory() {
  const r = useResource(api.faturas);
  const [params] = useSearchParams();
  const [search, setSearch] = useState(params.get('busca') ?? '');
  const rows = r.data?.filter(c => `${c.tipo} ${c.competencia} ${c.prefixo} ${c.solicitado_por}`.toLowerCase().includes(search.toLowerCase()));
  return <><div className="page-title"><h1>Faturas</h1><p>Histórico de faturas confirmadas pelo Checker, da mais recente para a mais antiga.</p></div><section className="card"><label>Buscar fatura<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Tipo, competência, prefixo ou Maker" /></label>{r.loading && <p role="status">Carregando…</p>}{r.error && <p role="alert">{r.error}<button onClick={r.reload}>Tentar novamente</button></p>}<div className="table-wrap"><table><thead><tr>{['Fatura','Tipo','Competência','Prefixo','Valor','Solicitado por','Confirmado por','Data da confirmação'].map(h => <th key={h}>{h}</th>)}</tr></thead><tbody>{rows?.map(c => <tr key={c.id_fatura}><td>#{c.id_fatura}</td><td>{c.tipo === 'agua' ? 'Água' : 'Energia'}</td><td>{c.competencia}</td><td>{c.prefixo}</td><td>{money(c.valor)}</td><td>{c.solicitado_por}</td><td>{c.confirmado_por}</td><td>{new Date(c.data_confirmacao).toLocaleString('pt-BR')}</td></tr>)}</tbody></table></div>{!r.loading && !r.error && !rows?.length && <p>Nenhuma fatura aprovada encontrada.</p>}</section></>;
}
