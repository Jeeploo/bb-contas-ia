import type { ComponentType } from 'react';
import { CircleCheck, CircleDashed, HelpCircle, TriangleAlert } from 'lucide-react';

export type StatusFaturaId = 'em_processamento' | 'validada' | 'revisao_necessaria';

export interface StatusFatura {
  id: StatusFaturaId | 'desconhecido';
  label: string;
}

// Nomes alternativos que a API pode usar para cada status.
const ALIASES: Record<StatusFaturaId, string[]> = {
  em_processamento: ['em_processamento', 'processando', 'em_processo', 'pendente', 'pendente_checker', 'aguardando_checker'],
  validada: ['validada', 'validado', 'aprovada', 'aprovado', 'confirmada', 'confirmada_checker'],
  revisao_necessaria: ['revisao_necessaria', 'revisao', 'reprovada', 'reprovado', 'rejeitada', 'rejeitado', 'devolvida'],
};
const LABEL: Record<StatusFaturaId, string> = {
  em_processamento: 'Em processamento',
  validada: 'Validada',
  revisao_necessaria: 'Revisão necessária',
};

/** Ponto único de mapeamento do status vindo da API/mock para os selos da tela.
 *  Sem status: o endpoint /faturas só devolve faturas confirmadas pelo Checker → "Validada". */
export function getStatusFatura(status?: string | null): StatusFatura {
  if (!status) return { id: 'validada', label: LABEL.validada };
  const chave = status.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[\s-]+/g, '_');
  const id = (Object.keys(ALIASES) as StatusFaturaId[]).find((k) => ALIASES[k].includes(chave));
  return id ? { id, label: LABEL[id] } : { id: 'desconhecido', label: status };
}

const ICONE: Record<StatusFatura['id'], ComponentType<{ size?: number; strokeWidth?: number; fill?: string; stroke?: string; 'aria-hidden'?: boolean }>> = {
  em_processamento: CircleDashed,
  validada: CircleCheck,
  revisao_necessaria: TriangleAlert,
  desconhecido: HelpCircle,
};

export function StatusBadge({ status }: { status: StatusFatura }) {
  const Icone = ICONE[status.id];
  // Triângulo de alerta preenchido: corpo vermelho, "!" na cor do fundo do selo.
  const extra = status.id === 'revisao_necessaria' ? { fill: '#C62828', stroke: '#FDE4E4' } : {};
  return (
    // Só ícone + cor; o texto fica no tooltip e para leitores de tela.
    <span className={`status-fatura status-fatura--${status.id}`} role="img" aria-label={status.label} title={status.label}>
      <Icone size={18} strokeWidth={2.2} aria-hidden={true} {...extra} />
    </span>
  );
}
