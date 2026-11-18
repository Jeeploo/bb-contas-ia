import type { ComponentType } from 'react';
import { ArrowDown, ArrowUp, CircleDollarSign, Droplet, FileCheck2, Zap } from 'lucide-react';
import type { Indicador, RelatorioFinanceiro } from '../../services/relatoriosService';
import { brl, inteiro, percentual } from './format';

interface KpiDef {
  key: keyof RelatorioFinanceiro['kpis'];
  label: string;
  Icon: ComponentType<{ size?: number; 'aria-hidden'?: boolean }>;
  tone: 'blue' | 'yellow';
  /** true: alta é boa (verde). false: queda é boa (gastos). */
  altaBoa: boolean;
  fmt: (v: number) => string;
}

const KPIS: KpiDef[] = [
  { key: 'total', label: 'Gasto total', Icon: CircleDollarSign, tone: 'blue', altaBoa: false, fmt: brl },
  { key: 'energia', label: 'Gasto com energia', Icon: Zap, tone: 'yellow', altaBoa: false, fmt: brl },
  { key: 'agua', label: 'Gasto com água', Icon: Droplet, tone: 'blue', altaBoa: false, fmt: brl },
  { key: 'faturas', label: 'Faturas processadas', Icon: FileCheck2, tone: 'blue', altaBoa: true, fmt: inteiro },
];

function Selo({ ind, altaBoa }: { ind: Indicador; altaBoa: boolean }) {
  if (ind.variacao === null) return <span className="rf-kpi__badge is-neutral">Sem período anterior</span>;
  const v = ind.variacao;
  const bom = v === 0 ? null : (v > 0) === altaBoa;
  const cls = bom === null ? 'is-neutral' : bom ? 'is-good' : 'is-bad';
  const Seta = v > 0 ? ArrowUp : ArrowDown;
  return (
    <span className={`rf-kpi__badge ${cls}`} title="Variação em relação ao período anterior">
      {v !== 0 && <Seta size={12} strokeWidth={3} aria-hidden={true} />}{percentual(v)}
      <span className="rf-sr"> em relação ao período anterior</span>
    </span>
  );
}

export function KpiCards({ kpis }: { kpis: RelatorioFinanceiro['kpis'] }) {
  return (
    <div className="rf-kpis">
      {KPIS.map(({ key, label, Icon, tone, altaBoa, fmt }) => {
        const ind = kpis[key];
        return (
          <section key={key} className={`rf-card rf-kpi${ind ? '' : ' is-muted'}`} aria-label={label}>
            <span className={`rf-kpi__icon tone-${tone}`}><Icon size={24} aria-hidden={true} /></span>
            {/* resumo-campo-texto: mesmo rótulo/valor dos campos do "Resumo da fatura". */}
            <div className="rf-kpi__body resumo-campo-texto">
              <span>{label}</span>
              <strong>{ind ? fmt(ind.valor) : '—'}</strong>
              {ind ? <Selo ind={ind} altaBoa={altaBoa} /> : <span className="rf-kpi__badge is-neutral">Fora do filtro</span>}
            </div>
          </section>
        );
      })}
    </div>
  );
}
