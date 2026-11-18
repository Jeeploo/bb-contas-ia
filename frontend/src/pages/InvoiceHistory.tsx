import { useSearchParams } from 'react-router-dom';
import { useMemo, useState } from 'react';
import { Droplet, Zap } from 'lucide-react';
import { api } from '../api';
import { useResource, money } from '../components/ui';
import { StatusBadge, getStatusFatura } from '../components/faturas/StatusFatura';
import './faturas.css';
const tipoLabel = (tipo: string) => tipo === 'agua' ? 'Água' : 'Energia';
const prefixoNumero = (prefixo: string) => prefixo.match(/\d+/)?.[0] ?? prefixo;
const iconStyle = { verticalAlign: 'middle', marginRight: 6, flexShrink: 0 } as const;
const semAcento = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const COLUNAS = ['Status', 'Fatura', 'Tipo', 'Competência', 'Prefixo', 'Valor', 'Solicitado por', 'Confirmado por', 'Data da confirmação'];
export function InvoiceHistory() {
  const r = useResource(api.faturas);
  const [params] = useSearchParams();
  const [search, setSearch] = useState(params.get('busca') ?? '');
  // Mais recente → mais antiga, pela data da confirmação.
  const ordenadas = useMemo(() => r.data?.map(c => ({ ...c, statusInfo: getStatusFatura(c.status) }))
    .sort((a, b) => new Date(b.data_confirmacao).getTime() - new Date(a.data_confirmacao).getTime()), [r.data]);
  const termo = semAcento(search);
  const rows = ordenadas?.filter(c => semAcento(`${c.statusInfo.label} ${c.tipo} ${tipoLabel(c.tipo)} ${c.competencia} ${c.prefixo} ${c.solicitado_por}`).includes(termo));
  return <><div className="page-title"><h1>Faturas</h1><p>Histórico de faturas confirmadas pelo Checker, da mais recente para a mais antiga.</p></div><section className="card"><label>Buscar fatura<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Tipo, competência, prefixo ou Maker" /></label>{r.loading && <p role="status">Carregando…</p>}{r.error && <p role="alert">{r.error}<button onClick={r.reload}>Tentar novamente</button></p>}<div className="table-wrap faturas-table"><table><thead><tr>{COLUNAS.map(h => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{rows?.map(c => <tr key={c.id_fatura}><td><StatusBadge status={c.statusInfo} /></td><td>{c.id_fatura}</td><td>{c.tipo === 'agua' ? <Droplet size={16} color="#1E6FD9" aria-hidden="true" style={iconStyle} /> : <Zap size={16} color="#F5C400" fill="#F5C400" aria-hidden="true" style={iconStyle} />}<span style={{ verticalAlign: 'middle' }}>{tipoLabel(c.tipo)}</span></td><td>{c.competencia}</td><td>{prefixoNumero(c.prefixo)}</td><td>{money(c.valor)}</td><td>{c.solicitado_por}</td><td>{c.confirmado_por}</td><td>{new Date(c.data_confirmacao).toLocaleString('pt-BR')}</td></tr>)}</tbody></table></div>{!r.loading && !r.error && !rows?.length && <p>Nenhuma fatura aprovada encontrada.</p>}</section></>;
}
