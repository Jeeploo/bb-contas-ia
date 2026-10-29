import { InvoiceSummary, CalculationSummary, type SummaryField } from './InvoiceSummary';
import type { Calculo } from '../../types';
export function ValidationSummary({ fields, calculo, onBack, onConfirm }: { fields: SummaryField[]; calculo: Calculo; onBack: () => void; onConfirm: () => void }) {
  return <section className="card validation-card">
    <span className="eyebrow">REVISÃO FINAL</span>
    <h2>Dados prontos para validação</h2>
    <p>Confira as informações da fatura antes de continuar.</p>
    <InvoiceSummary fields={fields.filter(f => ['Tipo da fatura', 'Concessionária', 'Prefixo', 'Agência', 'Valor da fatura', 'Data de vencimento', 'Competência', 'Unidade consumidora'].includes(f.label))} />
    <CalculationSummary calculo={calculo} />
    <div className="actions"><button onClick={onBack}>Voltar</button><button className="primary" onClick={onConfirm}>Confirmar e continuar</button></div>
  </section>;
}
