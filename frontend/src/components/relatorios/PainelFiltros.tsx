// Painel "Filtrar" compartilhado pelas páginas de Relatórios
// (Financeiros e Operacionais • Consumo e Sustentabilidade).
//
// - usePainelFiltros: estado do painel (aberto, rascunho) + fechar com ESC/clique fora.
// - BotaoFiltrar:      botão azul com funil, selo de filtros ativos e seta.
// - PainelFiltros:     moldura animada + grade de campos + "Limpar filtros"/"Aplicar filtros".
// - CampoPeriodo, CamposLocal: campos reaproveitados (Mês/Ano/Intervalo; Região → Estado → Cidade → Agência).
import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { ChevronDown, Filter } from 'lucide-react';
import {
  opcoesAgencia, opcoesCidade, opcoesEstado,
  type OpcoesLocal, type OpcoesPeriodo, type Periodo,
} from '../../services/relatoriosService';
import { SearchSelect } from './SearchSelect';
import './relatoriosBase.css';

// ------------------------------------------------------------ Estado

export function usePainelFiltros<T>(aplicado: T) {
  const [aberto, setAberto] = useState(false);
  const [assentado, setAssentado] = useState(false);
  const [rascunho, setRascunho] = useState<T>(aplicado);
  const panelId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const botaoRef = useRef<HTMLButtonElement>(null);

  const abrir = () => { setRascunho(aplicado); setAssentado(false); setAberto(true); };
  const fechar = useCallback((devolverFoco = false) => {
    setAberto(false);
    setAssentado(false);
    if (devolverFoco) botaoRef.current?.focus();
  }, []);
  const alternar = () => (aberto ? fechar() : abrir());

  // Fecha sem aplicar: clique fora do painel/botão ou ESC.
  useEffect(() => {
    if (!aberto) return;
    const onDown = (e: MouseEvent) => {
      const alvo = e.target as Node;
      if (panelRef.current?.contains(alvo) || botaoRef.current?.contains(alvo)) return;
      fechar();
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') fechar(true); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [aberto, fechar]);

  return { aberto, assentado, setAssentado, rascunho, setRascunho, panelId, panelRef, botaoRef, alternar, fechar };
}

export type PainelState<T> = ReturnType<typeof usePainelFiltros<T>>;

// ------------------------------------------------------------ Botão

export function BotaoFiltrar<T>({ painel, ativos, disabled }: { painel: PainelState<T>; ativos: number; disabled?: boolean }) {
  return (
    <button
      ref={painel.botaoRef}
      type="button"
      className="primary rf-filtrar"
      aria-expanded={painel.aberto}
      aria-controls={painel.panelId}
      disabled={disabled}
      onClick={painel.alternar}
    >
      <Filter size={18} aria-hidden="true" />
      Filtrar
      {ativos > 0 && <span className="rf-filtrar__badge" aria-label={`${ativos} filtro${ativos > 1 ? 's' : ''} ativo${ativos > 1 ? 's' : ''}`}>{ativos}</span>}
      <ChevronDown size={18} className="rf-filtrar__chev" aria-hidden="true" />
    </button>
  );
}

// ------------------------------------------------------------ Painel

export function PainelFiltros<T>({ painel, podeAplicar, onApply, onClear, children }: {
  painel: PainelState<T>;
  podeAplicar: boolean;
  /** Recebe o rascunho para gravar na URL; o painel fecha em seguida. */
  onApply: (rascunho: T) => void;
  onClear: () => void;
  children: ReactNode;
}) {
  const { aberto, assentado } = painel;
  return (
    <div
      className={`rf-panel-wrap${aberto ? ' is-open' : ''}${assentado ? ' is-settled' : ''}`}
      onTransitionEnd={(e) => { if (aberto && e.target === e.currentTarget) painel.setAssentado(true); }}
    >
      <div className="rf-panel-clip">
        <div id={painel.panelId} ref={painel.panelRef} className="rf-card rf-panel" role="region" aria-label="Filtros do relatório" inert={!aberto}>
          <form
            className="rf-panel__grid"
            onSubmit={(e) => {
              e.preventDefault();
              if (!podeAplicar) return;
              onApply(painel.rascunho);
              painel.fechar(true);
            }}
          >
            {children}
            <div className="rf-panel__actions">
              <button type="button" onClick={onClear}>Limpar filtros</button>
              <button type="submit" className="primary" disabled={!podeAplicar}>Aplicar filtros</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------ Campos

const MODOS: { tipo: Periodo['tipo']; label: string }[] = [
  { tipo: 'mes', label: 'Mês' },
  { tipo: 'ano', label: 'Ano' },
  { tipo: 'intervalo', label: 'Intervalo' },
];

export function CampoPeriodo({ periodo: p, opcoes, mesPadrao, onChange }: {
  periodo: Periodo;
  opcoes: OpcoesPeriodo;
  mesPadrao: string;
  onChange: (p: Periodo) => void;
}) {
  const erroId = useId();
  const trocarModo = (tipo: Periodo['tipo']) => {
    if (tipo === p.tipo) return;
    const mesBase = p.tipo === 'mes' ? p.mes : mesPadrao;
    if (tipo === 'mes') onChange({ tipo: 'mes', mes: mesBase });
    if (tipo === 'ano') onChange({ tipo: 'ano', ano: mesBase.slice(0, 4) });
    if (tipo === 'intervalo') onChange({ tipo: 'intervalo', de: `${mesBase}-01`, ate: opcoes.dataMax });
  };
  const intervaloInvalido = p.tipo === 'intervalo' && !!p.de && !!p.ate && p.ate < p.de;

  return (
    <fieldset className="rf-field rf-field--periodo">
      <legend>Período</legend>
      <div className="rf-seg" role="group" aria-label="Tipo de período">
        {MODOS.map((m) => (
          <button key={m.tipo} type="button" aria-pressed={p.tipo === m.tipo} onClick={() => trocarModo(m.tipo)}>{m.label}</button>
        ))}
      </div>
      {p.tipo === 'mes' && (
        <select aria-label="Mês" value={p.mes} onChange={(e) => onChange({ tipo: 'mes', mes: e.target.value })}>
          {[...opcoes.meses].reverse().map((m) => <option key={m.id} value={m.id}>{m.longo}</option>)}
        </select>
      )}
      {p.tipo === 'ano' && (
        <select aria-label="Ano" value={p.ano} onChange={(e) => onChange({ tipo: 'ano', ano: e.target.value })}>
          {[...opcoes.anos].reverse().map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
      )}
      {p.tipo === 'intervalo' && (
        <div className="rf-range">
          <input type="date" aria-label="Data inicial" min={opcoes.dataMin} max={opcoes.dataMax} value={p.de}
            onChange={(e) => onChange({ ...p, de: e.target.value })} />
          <input type="date" aria-label="Data final" min={p.de || opcoes.dataMin} max={opcoes.dataMax} value={p.ate}
            aria-invalid={intervaloInvalido} aria-describedby={intervaloInvalido ? erroId : undefined}
            onChange={(e) => onChange({ ...p, ate: e.target.value })} />
        </div>
      )}
      {intervaloInvalido && <small id={erroId} className="rf-field__erro" role="alert">A data final não pode ser anterior à inicial.</small>}
    </fieldset>
  );
}

export interface ValoresLocal { regiao: string; estado: string; cidade: string; agencia: string }

/** Região → Estado → Cidade → Agência. Mudar um "pai" limpa os filhos. */
export function CamposLocal({ opcoes, valores: v, onChange }: {
  opcoes: OpcoesLocal;
  valores: ValoresLocal;
  onChange: (patch: Partial<ValoresLocal>) => void;
}) {
  const estados = opcoesEstado(opcoes, v.regiao);
  const cidades = opcoesCidade(opcoes, v.regiao, v.estado);
  const agencias = opcoesAgencia(opcoes, v.regiao, v.estado, v.cidade);
  return (
    <>
      <label className="rf-field">
        Região
        <select value={v.regiao} onChange={(e) => onChange({ regiao: e.target.value, estado: '', cidade: '', agencia: '' })}>
          <option value="">Todas as regiões</option>
          {opcoes.regioes.map((r) => <option key={r.id} value={r.id}>{r.nome}</option>)}
        </select>
      </label>
      <label className="rf-field">
        Estado
        <select value={v.estado} disabled={!estados.length} onChange={(e) => onChange({ estado: e.target.value, cidade: '', agencia: '' })}>
          <option value="">Todos os estados</option>
          {estados.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
        </select>
      </label>
      <SearchSelect
        label="Cidade" todosLabel="Todas as cidades" value={v.cidade} disabled={!cidades.length}
        options={cidades.map((c) => ({ value: c.id, label: c.nome }))}
        onChange={(x) => onChange({ cidade: x, agencia: '' })}
      />
      <SearchSelect
        label="Agência" todosLabel="Todas as agências" value={v.agencia} disabled={!agencias.length}
        options={agencias.map((a) => ({ value: a.id, label: a.nome }))}
        onChange={(x) => onChange({ agencia: x })}
      />
    </>
  );
}
