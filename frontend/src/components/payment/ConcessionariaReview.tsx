import type { ReactNode } from 'react';
import type { ExtracaoInteligente } from '../../types';
import { DocumentaryAlerts, Alert } from './DocumentaryAlerts';
export interface OpcaoConcessionaria { id_concessionaria: number; nome: string; ativo: boolean }
export function ConcessionariaReview({extracao, nome, busy, onAssociate, onCalculate, footerStart, footerEnd, children}: {
  extracao: ExtracaoInteligente; nome?: string; busy: boolean; onAssociate: () => void; onCalculate: () => void;
  footerStart?: ReactNode; footerEnd?: ReactNode; children?: ReactNode;
}) {
  const pending = extracao.pendencias?.some(p => p.tipo === 'CORRESPONDENCIA_CONCESSIONARIA');
  const concessionaria = String(extracao.evidencias_validacao_documental?.nome_concessionaria ?? '');
  return <section className="card validation-card validacao-card">
    <div className="upload-heading resumo-heading"><span className="section-number">3</span><div><h2>Validação e cálculo</h2><p>Confira os dados extraídos e analise a unidade antes de calcular a fatura</p></div></div>
    {children && <div className="validacao-corpo">{children}</div>}
    {pending ? <><Alert variant="warning"><strong>Pendência cadastral</strong><p>Concessionária sem correspondência</p></Alert>
      <p>Nome extraído do documento: <strong>{nome}</strong></p><p>Correspondência cadastral: Não encontrada</p>
      <p>Pendência que não impede continuar. A associação é opcional para a demonstração.</p>
      <button disabled={busy} onClick={onAssociate}>Associar concessionária (opcional)</button></>
      : <div className="validacao-info"><Alert variant="info"><strong>Dados documentais disponíveis</strong>
        <p className="validacao-info-linha"><span>Nome extraído do documento: <strong>{nome}</strong></span>{concessionaria && <span>Concessionária: <strong>{concessionaria}</strong></span>}</p></Alert></div>}
    <DocumentaryAlerts extracao={{...extracao, pendencias: extracao.pendencias?.filter(p => p.tipo !== "CORRESPONDENCIA_CONCESSIONARIA")}} concessionaria={nome} confirmado />
    {(footerStart || footerEnd || !extracao.bloqueia_calculo) && <div className="actions">{footerStart}{footerEnd ?? (!extracao.bloqueia_calculo && <button className="primary" disabled={busy} onClick={onCalculate}>Calcular fatura</button>)}</div>}
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
      {error && <Alert variant="warning">{error}</Alert>}
      <div className="actions"><button type="button" disabled={busy} onClick={onClose}>Cancelar</button>
        <button className="primary" disabled={busy || !selected}>Confirmar associação</button></div>
    </form>
  </dialog>;
}
