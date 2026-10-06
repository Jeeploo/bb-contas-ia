import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { errorMessage } from '../api/client';
import type { Decimal } from '../types';
export const money = (value: Decimal) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value));
export const date = (value: string) => new Date(value.length === 10 ? value + 'T12:00:00' : value).toLocaleDateString('pt-BR');
export const confidence = (value: Decimal | null) => value === null ? 'Não informada' : `${Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
export function Badge({ value }: {
    value: string;
}) { return <span className={`badge ${/aprovad|validada|conclu/i.test(value) ? 'good' : /rejeitad|erro/i.test(value) ? 'bad' : ''}`}>{value.replaceAll('_', ' ')}</span>; }
export function Notice({ children, kind = 'success' }: {
    children: ReactNode;
    kind?: 'success' | 'error';
}) { return <div className={`notice ${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</div>; }
export function useResource<T>(loader: () => Promise<T>) {
    const [data, setData] = useState<T>();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [revision, setRevision] = useState(0);
    const reload = useCallback(() => setRevision(v => v + 1), []);
    useEffect(() => { let active = true; setLoading(true); setError(''); loader().then(value => { if (active)
        setData(value); }).catch(e => { if (active)
        setError(errorMessage(e)); }).finally(() => { if (active)
        setLoading(false); }); return () => { active = false; }; }, [loader, revision]);
    return { data, loading, error, reload };
}
export function ResourceState({ loading, error, empty, retry, children }: {
    loading: boolean;
    error: string;
    empty?: boolean;
    retry: () => void;
    children: ReactNode;
}) {
    return <>{loading && <div className="state" role="status"><RefreshCw className="spin"/> Carregando dados…</div>}{error ? <div className="state"><AlertCircle /><Notice kind="error">{error}</Notice><button onClick={retry}>Tentar novamente</button></div> : empty && !loading ? <div className="state">Nenhum registro disponível.</div> : children}</>;
}
export function PageTitle({ title, subtitle, action }: {
    title: string;
    subtitle: string;
    action?: ReactNode;
}) { return <div className="page-title"><div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>; }
export interface Column<T> {
    title: string;
    render: (row: T) => ReactNode;
}
export function Table<T>({ rows, columns, rowKey }: {
    rows: T[];
    columns: Column<T>[];
    rowKey: (row: T) => number;
}) { if (!rows.length)
    return <div className="state">Nenhum registro disponível.</div>; return <div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c.title}>{c.title}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={rowKey(row)}>{columns.map(c => <td key={c.title}>{c.render(row)}</td>)}</tr>)}</tbody></table></div>; }
