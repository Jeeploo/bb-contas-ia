// Grade de campos do passo 2 ("Resumo da fatura"): ícone, rótulo/valor e lápis de edição.
import type { ReactNode } from 'react';
import { Barcode, Building2, CalendarDays, CircleDollarSign, Droplet, FileText, Landmark, Pencil, UserRound, Zap } from 'lucide-react';

export type ResumoCampo = { label: string; value: string; onEdit: () => void };

const tipoTexto = (v: string) => ({ CONTA_ENERGIA: 'Energia', ENERGIA: 'Energia', CONTA_AGUA: 'Água', AGUA: 'Água', OUTRO: 'Outro' } as Record<string, string>)[v] ?? v;
const isAgua = (v: string) => /[aá]gua|saneamento/i.test(v);

function icone(label: string, value: string): ReactNode {
  const p = { size: 20, 'aria-hidden': true } as const;
  switch (label) {
    case 'Tipo da fatura': return isAgua(value) ? <Droplet {...p} /> : <Zap {...p} />;
    case 'Valor da fatura': return <CircleDollarSign {...p} />;
    case 'Data de vencimento': return <CalendarDays {...p} />;
    case 'Prefixo':
    case 'Agência':
    case 'Unidade': return <Landmark {...p} />;
    case 'Concessionária': return <Building2 {...p} />;
    case 'Responsável': return <UserRound {...p} />;
    default: return <Barcode {...p} />;
  }
}

function formatar(label: string, value: string) {
  if (label === 'Data de vencimento' && /^\d{4}-\d{2}-\d{2}$/.test(value)) return value.split('-').reverse().join('/');
  if (label === 'Tipo da fatura') { const t = tipoTexto(value); return isAgua(t) ? 'Água' : /energia/i.test(t) ? 'Energia' : t; }
  return value;
}

export function ResumoCampos({ campos, readOnly = false }: { campos: ResumoCampo[]; readOnly?: boolean }) {
  return (
    <div className="resumo-campos">
      {campos.map(c => (
        <div key={c.label} className={`resumo-campo${c.label === 'Código de barras' ? ' resumo-campo-largo' : ''}`}>
          <span className="resumo-campo-icone">{icone(c.label, c.value)}</span>
          <div className="resumo-campo-texto">
            <span>{c.label}</span>
            <strong title={c.value}>{formatar(c.label, c.value)}</strong>
          </div>
          <button type="button" className="resumo-campo-editar" onClick={c.onEdit} disabled={readOnly} aria-label={`Editar ${c.label}`} title={`Editar ${c.label}`}>
            <Pencil size={14} aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>
  );
}

/** Lista compacta "Resumo da fatura" da etapa 3: ícone | rótulo | valor à direita. */
export function ResumoLista({ linhas }: { linhas: { label: string; titulo?: string; value: string }[] }) {
  return (
    <section className="resumo-lista" aria-label="Resumo da fatura">
      <h3><FileText size={18} aria-hidden="true" /> Resumo da fatura</h3>
      <dl>
        {linhas.map(l => (
          <div key={l.label}>
            <dt><span className="resumo-lista-icone">{icone(l.label, l.value)}</span>{l.titulo ?? l.label}</dt>
            <dd title={l.value}>{formatar(l.label, l.value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
