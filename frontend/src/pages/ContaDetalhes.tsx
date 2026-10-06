import { useCallback, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import { errorMessage } from '../api/client';
import { Badge, Notice, PageTitle, ResourceState, Table, money, date, confidence, useResource } from '../components/ui';
import { ValidationTable } from '../components/ValidationTable';
import type { ProcessamentoDocumento } from '../types';
export function ContaDetalhes() {
    const id = Number(useParams().id);
    const load = useCallback(async () => { const [conta, documentos, extracoes, dados, calculos, ordens] = await Promise.all([api.conta(id), api.documentos(), api.extracoes(), api.dados(), api.calculos(), api.ordens()]); const docs = documentos.filter(d => d.id_conta === id); const exts = extracoes.filter(e => docs.some(d => d.id_documento === e.id_documento)); return { conta, documentos: docs, extracoes: exts, dados: dados.filter(d => exts.some(e => e.id_extracao === d.id_extracao)), calculos: calculos.filter(c => c.id_conta === id), ordens: ordens.filter(o => calculos.some(c => c.id_conta === id && c.id_calculo === o.id_calculo)) }; }, [id]);
    const r = useResource(load);
    const [file, setFile] = useState<File>();
    const input = useRef<HTMLInputElement>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [result, setResult] = useState<ProcessamentoDocumento>();
    async function action(task: () => Promise<void>) { setBusy(true); setError(''); setSuccess(''); try {
        await task();
        r.reload();
    }
    catch (e) {
        setError(errorMessage(e));
    }
    finally {
        setBusy(false);
    } }
    return <><PageTitle title={`Conta #${id}`} subtitle="Documentos, extração e etapas seguintes" action={<Link to="/contas">Voltar às contas</Link>}/>{error && <Notice kind="error">{error}</Notice>}{success && <Notice>{success}</Notice>}<ResourceState {...r} retry={r.reload}>{r.data && <><div className="summary"><article><span>Competência</span><strong>{r.data.conta.competencia}</strong></article><article><span>Vencimento</span><strong>{date(r.data.conta.data_vencimento)}</strong></article><article><span>Valor original</span><strong>{money(r.data.conta.valor_original)}</strong></article><article><span>Situação</span><Badge value={r.data.conta.situacao}/></article></div><section className="panel"><h2>Upload e processamento</h2><p>Envie um PDF e processe o documento para revisar os campos extraídos.</p><form className="upload" onSubmit={e => { e.preventDefault(); if (file)
        void action(async () => { await api.upload(id, file); setFile(undefined); if (input.current)
            input.current.value = ''; setSuccess('PDF enviado. Selecione Processar para iniciar a extração.'); }); }}><input ref={input} type="file" accept="application/pdf,.pdf" aria-label="Selecionar PDF" disabled={busy} onChange={e => setFile(e.target.files?.[0])}/><button className="primary" disabled={busy || !file}>{busy ? 'Aguarde…' : 'Enviar PDF'}</button></form><Table rows={r.data.documentos} rowKey={d => d.id_documento} columns={[{ title: 'Documento', render: d => `#${d.id_documento} · ${d.formato}` }, { title: 'Recebido', render: d => date(d.data_recebimento) }, { title: 'Status / confiança', render: d => { const ext = r.data?.extracoes.filter(e => e.id_documento === d.id_documento).sort((a, b) => b.id_extracao - a.id_extracao)[0]; return ext ? <><Badge value={ext.situacao_validacao}/><small>{confidence(ext.nivel_confianca)}</small></> : 'Recebido · não processado'; } }, { title: 'Estratégia', render: d => r.data?.extracoes.find(e => e.id_documento === d.id_documento)?.estrategia ?? (result?.documento.id_documento === d.id_documento ? result.estrategia ?? result.extracao.estrategia : undefined) ?? 'Não informada pela API' }, { title: 'Ação', render: d => <button disabled={busy} onClick={() => void action(async () => { const response = await api.processar(d.id_documento); setResult(response); setSuccess(`Processamento concluído: ${response.situacao}. Confiança: ${confidence(response.confianca_geral)}.`); })}>Processar</button> }]}/></section><section className="panel"><h2>Campos extraídos e validação</h2><p>Confirme o original ou edite o valor validado e envie a correção. O valor extraído é preservado.</p><ValidationTable dados={r.data.dados} reload={r.reload}/></section><section className="panel"><h2>Cálculos vinculados</h2><Table rows={r.data.calculos} rowKey={c => c.id_calculo} columns={[{ title: 'ID / regra', render: c => `#${c.id_calculo} / #${c.id_regra}` }, { title: 'Valor inicial', render: c => money(c.valor_inicial) }, { title: 'Valor calculado', render: c => money(c.valor_calculado) }, { title: 'Situação', render: c => <Badge value={c.situacao}/> }]}/></section><section className="panel"><h2>Ordens vinculadas</h2><Table rows={r.data.ordens} rowKey={o => o.id_ordem} columns={[{ title: 'Ordem', render: o => <Link to={`/ordens/${o.id_ordem}`}>#{o.id_ordem} · Abrir</Link> }, { title: 'Total', render: o => money(o.valor_total) }, { title: 'Situação', render: o => <Badge value={o.situacao}/> }]}/></section></>}</ResourceState></>;
}
