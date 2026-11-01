import { useAuth } from '../auth/AuthContext';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { errorMessage } from '../api/client';
import { Badge, Notice, PageTitle, ResourceState, Table, money, date, useResource } from '../components/ui';
import type { OrdemPagamento, Usuario, Alcada } from '../types';
const load = async () => { const [ordens, usuarios, alcadas, aprovacoes] = await Promise.all([api.ordens(), api.usuarios(), api.alcadas(), api.aprovacoes()]); return { ordens, usuarios, alcadas, aprovacoes }; };
function Decision({ ordem, usuarios, alcadas, reload }: {
    ordem: OrdemPagamento;
    usuarios: Usuario[];
    alcadas: Alcada[];
    reload: () => void;
}) {
    const { session } = useAuth();
    const user = session?.usuario.id_usuario;
    const [obs, setObs] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const selected = usuarios.find(u => u.id_usuario === Number(user));
    const alcada = alcadas.find(a => a.id_alcada === selected?.id_alcada);
    async function decide(decisao: 'aprovado' | 'rejeitado') { setBusy(true); setError(''); setSuccess(''); try {
        await api.decidir(ordem.id_ordem, decisao, obs);
        setSuccess(`Decisão registrada: ${decisao}.`);
        reload();
    }
    catch (e) {
        setError(errorMessage(e));
    }
    finally {
        setBusy(false);
    } }
    return <div className="decision"><p>Aprovador: {session?.usuario.nome}</p><small>Alçada: {alcada ? `${alcada.nome_nivel} · ${money(alcada.limite_financeiro)}` : 'Não informada'}</small><input aria-label={`Observação para ordem ${ordem.id_ordem}`} placeholder="Observação (opcional)" value={obs} onChange={e => setObs(e.target.value)} disabled={busy}/><div className="button-row"><button className="primary" disabled={!user || busy} onClick={() => void decide('aprovado')}>Aprovar</button><button className="danger" disabled={!user || busy} onClick={() => void decide('rejeitado')}>Rejeitar</button></div>{busy && <small role="status">Enviando decisão…</small>}{error && <Notice kind="error">{error}</Notice>}{success && <Notice>{success}</Notice>}</div>;
}
export function Aprovacoes() { const r = useResource(load); const [params] = useSearchParams(); const filter = Number(params.get('ordem')); return <><PageTitle title="Aprovações" subtitle="Demonstração de decisões com controle de alçada no backend" action={<button onClick={r.reload}>Atualizar</button>}/><p className="hint">A decisão utiliza o usuário da sessão autenticada. As regras de autoaprovação e alçada são verificadas pela API.</p><ResourceState {...r} retry={r.reload}>{r.data && <><Table rows={r.data.ordens.filter(o => !filter || o.id_ordem === filter)} rowKey={o => o.id_ordem} columns={[{ title: 'Ordem', render: o => <Link to={`/ordens/${o.id_ordem}`}>#{o.id_ordem}</Link> }, { title: 'Valor', render: o => money(o.valor_total) }, { title: 'Criador', render: o => r.data?.usuarios.find(u => u.id_usuario === o.id_usuario_criador)?.nome ?? `#${o.id_usuario_criador}` }, { title: 'Situação', render: o => <Badge value={o.situacao}/> }, { title: 'Aprovador / alçada / decisão', render: o => r.data && <Decision ordem={o} usuarios={r.data.usuarios} alcadas={r.data.alcadas} reload={r.reload}/> }]}/><section className="panel"><h2>Histórico de decisões</h2><Table rows={r.data.aprovacoes.filter(a => !filter || a.id_ordem === filter)} rowKey={a => a.id_aprovacao} columns={[{ title: 'Ordem', render: a => `#${a.id_ordem}` }, { title: 'Aprovador', render: a => r.data?.usuarios.find(u => u.id_usuario === a.id_usuario)?.nome ?? `#${a.id_usuario}` }, { title: 'Decisão', render: a => <Badge value={a.decisao}/> }, { title: 'Data', render: a => date(a.data_hora) }, { title: 'Observação', render: a => a.observacao ?? '—' }]}/></section></>}</ResourceState></>; }
