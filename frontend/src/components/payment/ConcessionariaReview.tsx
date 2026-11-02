import type { ExtracaoInteligente } from '../../types';
import { DocumentaryAlerts, Alert } from './DocumentaryAlerts';
export interface OpcaoConcessionaria { id_concessionaria: number; nome: string; ativo: boolean }
export function ConcessionariaReview({extracao, nome, busy, onAssociate, onCalculate}: {
  extracao: ExtracaoInteligente; nome?: string; busy: boolean; onAssociate: () => void; onCalculate: () => void;
}) {
  const pending = extracao.pendencias?.some(p => p.tipo === 'CORRESPONDENCIA_CONCESSIONARIA');
  return <section className="card validation-card">
    <h2>Documento enviado para validação</h2>
    {pending ? <><Alert variant="review"><strong>Pendência cadastral</strong><p>Concessionária sem correspondência</p></Alert>
      <p>Nome extraído do documento: <strong>{nome}</strong></p><p>Correspondência cadastral: Não encontrada</p>
      <button className="primary" disabled={busy} onClick={onAssociate}>Associar concessionária</button></>
      : <><Alert variant="info"><strong>Correspondência cadastral resolvida</strong></Alert>
        <p>Nome extraído do documento: <strong>{nome}</strong></p>
        <p>Concessionária: {String(extracao.evidencias_validacao_documental?.nome_concessionaria ?? '')}</p></>}
    <DocumentaryAlerts extracao={{...extracao, pendencias: extracao.pendencias?.filter(p => p.tipo !== "CORRESPONDENCIA_CONCESSIONARIA")}} concessionaria={nome} confirmado />
    {!extracao.bloqueia_calculo && <div className="actions"><button className="primary" disabled={busy} onClick={onCalculate}>Calcular fatura</button></div>}
  </section>;
}
export function AssociarConcessionariaModal({nome, opcoes, selected, busy, error, onSelect, onClose, onConfirm}: {
  nome?: string; opcoes: OpcaoConcessionaria[]; selected: number; busy: boolean; error: string;
  onSelect: (id: number) => void; onClose: () => void; onConfirm: () => void;
}) {
  return <dialog ref={element => { if (element && !element.open) element.showModal(); }} aria-labelledby="associate-title"
    onCancel={e => {e.preventDefault(); if (!busy) onClose();}}>
    <form onSubmit={e => { e.preventDefault(); onConfirm(); }}>
      <h2 id="associate-title">Associar concessionária</h2>
      <p>Extraído do documento</p><p><strong>{nome}</strong></p>
      <label>Associar a:<select required value={selected || ''} disabled={busy} onChange={e => onSelect(Number(e.target.value))}>
        <option value="" disabled>Selecione uma concessionária cadastrada</option>
        {opcoes.map(c => <option key={c.id_concessionaria} value={c.id_concessionaria}>{c.nome}</option>)}
      </select></label>
      {error && <p className="notice error" role="alert">{error}</p>}
      <div className="actions"><button type="button" disabled={busy} onClick={onClose}>Cancelar</button>
        <button className="primary" disabled={busy || !selected}>Confirmar associação</button></div>
    </form>
  </dialog>;
}
