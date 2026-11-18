import { useEffect, useMemo, useState, type ComponentType } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Droplet, FileText, Leaf, Recycle, Zap } from 'lucide-react';
import { BotaoFiltrar, CampoPeriodo, CamposLocal, PainelFiltros, usePainelFiltros } from '../components/relatorios/PainelFiltros';
import { SearchSelect } from '../components/relatorios/SearchSelect';
import { ConsumoTabela, UNIDADE, formatarConsumo } from '../components/relatorios/ConsumoTabela';
import { MES_PADRAO } from '../mocks/relatoriosMock';
import {
  getOpcoesConsumo, getRelatorioConsumo,
  type FiltrosConsumo, type OpcoesConsumo, type RelatorioConsumo, type TipoConsumo,
} from '../services/consumoService';
import {
  PERIODO_PADRAO, mesmoPeriodo, normalizarLocal, periodoParaTexto, periodoValido, textoParaPeriodo,
} from '../services/relatoriosService';
import './relatorios.css';
import './relatoriosConsumo.css';

type IconType = ComponentType<{ size?: number; strokeWidth?: number; 'aria-hidden'?: boolean }>;

const TIPOS: { tipo: TipoConsumo; rotulo: [string, string]; nome: string; Icon: IconType }[] = [
  { tipo: 'agua', rotulo: ['Consumo de', 'água'], nome: 'Água', Icon: Droplet },
  { tipo: 'energia', rotulo: ['Consumo de', 'energia'], nome: 'Energia', Icon: Zap },
  { tipo: 'papel', rotulo: ['Consumo de', 'papel'], nome: 'Papel', Icon: FileText },
  { tipo: 'residuos', rotulo: ['Consumo de', 'resíduos'], nome: 'Resíduos', Icon: Recycle },
];
const TIPO_PADRAO: TipoConsumo = 'agua';

type Rascunho = FiltrosConsumo & { tipo: TipoConsumo };
const PADRAO: Rascunho = {
  tipo: TIPO_PADRAO, periodo: PERIODO_PADRAO,
  regiao: '', estado: '', cidade: '', agencia: '', superintendencia: '', diretoria: '',
};

// Chaves curtas na URL para Superintendência e Diretoria.
const URL_CHAVE = { superintendencia: 'super', diretoria: 'dir' } as const;

function lerUrl(params: URLSearchParams, opcoes: OpcoesConsumo | null): Rascunho {
  const t = params.get('tipo');
  const tipo = TIPOS.some((x) => x.tipo === t) ? (t as TipoConsumo) : TIPO_PADRAO;
  if (!opcoes) return { ...PADRAO, tipo };
  const per = textoParaPeriodo(params.get('periodo'));
  const sup = params.get(URL_CHAVE.superintendencia) ?? '';
  const dir = params.get(URL_CHAVE.diretoria) ?? '';
  return normalizarLocal({
    tipo,
    periodo: per && periodoValido(per, opcoes) ? per : PERIODO_PADRAO,
    regiao: params.get('regiao') ?? '',
    estado: params.get('estado') ?? '',
    cidade: params.get('cidade') ?? '',
    agencia: params.get('agencia') ?? '',
    superintendencia: opcoes.superintendencias.some((s) => s.pfx === sup) ? sup : '',
    diretoria: opcoes.diretorias.some((d) => d.pfx === dir) ? dir : '',
  }, opcoes);
}

function escreverUrl(r: Rascunho): URLSearchParams {
  const p = new URLSearchParams();
  if (r.tipo !== TIPO_PADRAO) p.set('tipo', r.tipo);
  if (!mesmoPeriodo(r.periodo, PERIODO_PADRAO)) p.set('periodo', periodoParaTexto(r.periodo));
  (['regiao', 'estado', 'cidade', 'agencia'] as const).forEach((k) => { if (r[k]) p.set(k, r[k]); });
  if (r.superintendencia) p.set(URL_CHAVE.superintendencia, r.superintendencia);
  if (r.diretoria) p.set(URL_CHAVE.diretoria, r.diretoria);
  return p;
}

const contarAtivos = (r: Rascunho) => [
  r.tipo !== TIPO_PADRAO, !mesmoPeriodo(r.periodo, PERIODO_PADRAO),
  r.regiao, r.estado, r.cidade, r.agencia, r.superintendencia, r.diretoria,
].filter(Boolean).length;

export function RelatoriosConsumo() {
  const [params, setParams] = useSearchParams();
  const [opcoes, setOpcoes] = useState<OpcoesConsumo | null>(null);
  const [dados, setDados] = useState<RelatorioConsumo | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let vivo = true;
    getOpcoesConsumo()
      .then((o) => { if (vivo) setOpcoes(o); })
      .catch((e: unknown) => { if (vivo) { setErro(e instanceof Error ? e.message : 'Não foi possível carregar os filtros.'); setCarregando(false); } });
    return () => { vivo = false; };
  }, [tentativa]);

  const aplicado = useMemo(() => lerUrl(params, opcoes), [params, opcoes]);
  const painel = usePainelFiltros<Rascunho>(aplicado);

  // O tipo de consumo só troca a coluna exibida: não precisa buscar de novo.
  const { tipo, ...filtros } = aplicado;
  const chave = JSON.stringify(filtros);
  useEffect(() => {
    if (!opcoes) return;
    let vivo = true;
    setCarregando(true);
    setErro(null);
    getRelatorioConsumo(JSON.parse(chave) as FiltrosConsumo)
      .then((d) => { if (vivo) setDados(d); })
      .catch((e: unknown) => { if (vivo) setErro(e instanceof Error ? e.message : 'Não foi possível carregar o relatório.'); })
      .finally(() => { if (vivo) setCarregando(false); });
    return () => { vivo = false; };
  }, [chave, opcoes, tentativa]);

  const aplicar = (r: Rascunho) => setParams(escreverUrl(normalizarLocal(r, opcoes!)), { replace: true });
  const selecionarTipo = (t: TipoConsumo) => aplicar({ ...aplicado, tipo: t });

  const draft = painel.rascunho;
  const set = (patch: Partial<Rascunho>) => painel.setRascunho({ ...draft, ...patch });

  return (
    <div className="rf-page rc-page">
      {/* Mesmas classes do título de "Pagamento de faturas" (page-title + payment-title). */}
      <div className="page-title payment-title">
        <div>
          <h1><Leaf className="rel-title-icon rc-leaf" aria-hidden="true" />Relatórios de Consumo e Sustentabilidade</h1>
          <p>Acompanhe os dados de consumo e o impacto ambiental da sua agência.</p>
        </div>
        <BotaoFiltrar painel={painel} ativos={contarAtivos(aplicado)} disabled={!opcoes} />
      </div>
      <Link to="/relatorios" className="rc-back">← Voltar para Relatórios</Link>

      {opcoes && (
        <PainelFiltros
          painel={painel}
          podeAplicar={periodoValido(draft.periodo, opcoes)}
          onApply={aplicar}
          onClear={() => painel.setRascunho(PADRAO)}
        >
          <label className="rf-field">
            Tipo de consumo
            <select value={draft.tipo} onChange={(e) => set({ tipo: e.target.value as TipoConsumo })}>
              {TIPOS.map((t) => <option key={t.tipo} value={t.tipo}>{t.nome}</option>)}
            </select>
          </label>
          <CampoPeriodo periodo={draft.periodo} opcoes={opcoes} mesPadrao={MES_PADRAO} onChange={(periodo) => set({ periodo })} />
          <CamposLocal opcoes={opcoes} valores={draft} onChange={set} />
          <SearchSelect
            label="Superintendência" todosLabel="Todas as superintendências" value={draft.superintendencia}
            options={opcoes.superintendencias.map((s) => ({ value: s.pfx, label: `${s.pfx} — ${s.nome}` }))}
            onChange={(v) => set({ superintendencia: v })}
          />
          <SearchSelect
            label="Diretoria" todosLabel="Todas as diretorias" value={draft.diretoria}
            options={opcoes.diretorias.map((d) => ({ value: d.pfx, label: `${d.pfx} — ${d.nome}` }))}
            onChange={(v) => set({ diretoria: v })}
          />
        </PainelFiltros>
      )}

      {erro && (
        <div className="rf-card rc-erro" role="alert">
          <p>{erro}</p>
          <button type="button" onClick={() => setTentativa((t) => t + 1)}>Tentar novamente</button>
        </div>
      )}
      {!dados && carregando && !erro && <p role="status" className="rc-status">Carregando relatório…</p>}

      {dados && (
        <div className={`rc-content${carregando ? ' is-loading' : ''}`} aria-busy={carregando}>
          <div className="rc-cards" role="group" aria-label="Tipo de consumo exibido na tabela">
            {TIPOS.map(({ tipo: t, rotulo, Icon }) => (
              <button
                key={t}
                type="button"
                className={`rc-card rc-card--${t}${t === tipo ? ' is-selected' : ''}`}
                aria-pressed={t === tipo}
                onClick={() => selecionarTipo(t)}
              >
                <span className="rc-card__head">
                  <Icon size={30} strokeWidth={1.6} aria-hidden={true} />
                  <span>{rotulo[0]}<br />{rotulo[1]}</span>
                </span>
                <span className="rc-card__valor">
                  <strong>{formatarConsumo(t, dados.totais[t])}</strong>
                  <span className="rc-card__sep" aria-hidden="true" />
                  <span>{UNIDADE[t]}</span>
                </span>
              </button>
            ))}
          </div>

          <ConsumoTabela linhas={dados.linhas} tipo={tipo} />
        </div>
      )}
    </div>
  );
}
