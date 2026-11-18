// Campos do painel "Filtrar" da página Relatórios Financeiros e Operacionais.
// A moldura, o comportamento e os campos comuns vêm de PainelFiltros.tsx.
import type { ComponentType } from 'react';
import { periodoValido, type FiltrosFinanceiros, type OpcoesFiltroFinanceiro, type TipoConta } from '../../services/relatoriosService';
import { MES_PADRAO } from '../../mocks/relatoriosMock';
import { CampoPeriodo, CamposLocal, PainelFiltros, type PainelState } from './PainelFiltros';

export interface Secao { value: string; label: string; Icon: ComponentType<{ size?: number; 'aria-hidden'?: boolean }> }
export type Rascunho = FiltrosFinanceiros & { secao: string };

export function FilterPanel({ painel, secoes, opcoes, onApply, onClear }: {
  painel: PainelState<Rascunho>;
  secoes: Secao[];
  opcoes: OpcoesFiltroFinanceiro;
  onApply: (r: Rascunho) => void;
  onClear: () => void;
}) {
  const draft = painel.rascunho;
  const set = (patch: Partial<Rascunho>) => painel.setRascunho({ ...draft, ...patch });

  return (
    <PainelFiltros painel={painel} podeAplicar={periodoValido(draft.periodo, opcoes)} onApply={onApply} onClear={onClear}>
      <label className="rf-field">
        Tipo de relatório
        <select value={draft.secao} onChange={(e) => set({ secao: e.target.value })}>
          {secoes.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </label>

      <CampoPeriodo periodo={draft.periodo} opcoes={opcoes} mesPadrao={MES_PADRAO} onChange={(periodo) => set({ periodo })} />

      <label className="rf-field">
        Tipo de conta
        <select value={draft.conta} onChange={(e) => set({ conta: e.target.value as TipoConta })}>
          <option value="">Todas</option>
          <option value="energia">Energia</option>
          <option value="agua">Água</option>
        </select>
      </label>

      <CamposLocal opcoes={opcoes} valores={draft} onChange={set} />
    </PainelFiltros>
  );
}
