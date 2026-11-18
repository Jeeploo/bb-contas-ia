import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ArrowLeftRight, BarChart3, FileCheck2, Gauge, LayoutGrid, MapPin,
  TrendingUp, TriangleAlert, Trophy,
} from 'lucide-react';
import { KpiCards } from '../components/relatorios/KpiCards';
import { EvolucaoCard, LocalCard } from '../components/relatorios/Graficos';
import { FilterPanel, type Rascunho, type Secao } from '../components/relatorios/FilterPanel';
import { BotaoFiltrar, usePainelFiltros } from '../components/relatorios/PainelFiltros';
import {
  FILTROS_PADRAO, getOpcoesFiltroFinanceiro, getRelatorioFinanceiro, mesmoPeriodo, normalizarLocal,
  periodoParaTexto, periodoValido, textoParaPeriodo,
  type FiltrosFinanceiros, type OpcoesFiltroFinanceiro, type RelatorioFinanceiro, type TipoConta,
} from '../services/relatoriosService';
import './relatorios.css';
import './relatoriosFinanceiros.css';

const SECOES: Secao[] = [
  { value: 'visao-geral', label: 'Visão geral', Icon: LayoutGrid },
  { value: 'evolucao', label: 'Evolução das despesas', Icon: TrendingUp },
  { value: 'localizacao', label: 'Gastos por localização', Icon: MapPin },
  { value: 'ranking', label: 'Ranking de agências', Icon: Trophy },
  { value: 'status', label: 'Status das faturas', Icon: FileCheck2 },
  { value: 'inconsistencias', label: 'Inconsistências', Icon: TriangleAlert },
  { value: 'eficiencia', label: 'Eficiência do processo', Icon: Gauge },
  { value: 'comparativo', label: 'Comparativo de períodos', Icon: ArrowLeftRight },
];
const SECAO_PADRAO = 'visao-geral';
const RASCUNHO_PADRAO: Rascunho = { ...FILTROS_PADRAO, secao: SECAO_PADRAO };

/** Lê seção + filtros da URL, validando contra as opções disponíveis. */
function lerUrl(params: URLSearchParams, opcoes: OpcoesFiltroFinanceiro | null): Rascunho {
  const secaoUrl = params.get('secao');
  const secao = SECOES.some((s) => s.value === secaoUrl) ? secaoUrl! : SECAO_PADRAO;
  if (!opcoes) return { ...RASCUNHO_PADRAO, secao };
  const periodoUrl = textoParaPeriodo(params.get('periodo'));
  const conta = params.get('conta');
  return normalizarLocal({
    secao,
    periodo: periodoUrl && periodoValido(periodoUrl, opcoes) ? periodoUrl : FILTROS_PADRAO.periodo,
    regiao: params.get('regiao') ?? '',
    estado: params.get('estado') ?? '',
    cidade: params.get('cidade') ?? '',
    agencia: params.get('agencia') ?? '',
    conta: (conta === 'energia' || conta === 'agua' ? conta : '') as TipoConta,
  }, opcoes);
}

/** Grava na URL só o que difere do padrão. */
function escreverUrl(r: Rascunho): URLSearchParams {
  const p = new URLSearchParams();
  if (r.secao !== SECAO_PADRAO) p.set('secao', r.secao);
  if (!mesmoPeriodo(r.periodo, FILTROS_PADRAO.periodo)) p.set('periodo', periodoParaTexto(r.periodo));
  (['regiao', 'estado', 'cidade', 'agencia', 'conta'] as const).forEach((k) => { if (r[k]) p.set(k, r[k]); });
  return p;
}

function contarAtivos(r: Rascunho) {
  return [
    r.secao !== SECAO_PADRAO,
    !mesmoPeriodo(r.periodo, FILTROS_PADRAO.periodo),
    r.regiao, r.estado, r.cidade, r.agencia, r.conta,
  ].filter(Boolean).length;
}

export function RelatoriosFinanceiros() {
  const [params, setParams] = useSearchParams();
  const [opcoes, setOpcoes] = useState<OpcoesFiltroFinanceiro | null>(null);
  const [dados, setDados] = useState<RelatorioFinanceiro | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let vivo = true;
    getOpcoesFiltroFinanceiro()
      .then((o) => { if (vivo) setOpcoes(o); })
      .catch((e: unknown) => { if (vivo) { setErro(e instanceof Error ? e.message : 'Não foi possível carregar os filtros.'); setCarregando(false); } });
    return () => { vivo = false; };
  }, [tentativa]);

  const aplicado = useMemo(() => lerUrl(params, opcoes), [params, opcoes]);
  const ativos = contarAtivos(aplicado);
  // Painel "Filtrar": rascunho só vira filtro aplicado em "Aplicar filtros".
  const painel = usePainelFiltros<Rascunho>(aplicado);

  const filtros: FiltrosFinanceiros = aplicado;
  const chaveFiltros = JSON.stringify({ ...filtros, secao: undefined });
  useEffect(() => {
    if (!opcoes) return;
    let vivo = true;
    setCarregando(true);
    setErro(null);
    getRelatorioFinanceiro(JSON.parse(chaveFiltros) as FiltrosFinanceiros)
      .then((d) => { if (vivo) setDados(d); })
      .catch((e: unknown) => { if (vivo) setErro(e instanceof Error ? e.message : 'Não foi possível carregar o relatório.'); })
      .finally(() => { if (vivo) setCarregando(false); });
    return () => { vivo = false; };
  }, [chaveFiltros, opcoes, tentativa]);

  const aplicar = (r: Rascunho) => setParams(escreverUrl(normalizarLocal(r, opcoes!)), { replace: true });

  const contextoLocal = (() => {
    if (!opcoes) return undefined;
    if (filtros.agencia || filtros.cidade) return opcoes.cidades.find((c) => c.id === (filtros.cidade || opcoes.agencias.find((a) => a.id === filtros.agencia)?.cidade))?.nome;
    if (filtros.estado) return opcoes.estados.find((e) => e.id === filtros.estado)?.nome;
    if (filtros.regiao) return opcoes.regioes.find((r) => r.id === filtros.regiao)?.nome;
    return undefined;
  })();

  const secao = aplicado.secao;
  const secaoAtual = SECOES.find((s) => s.value === secao)!;

  return (
    <div className="rf-page">
      {/* Mesmas classes do título de "Pagamento de faturas" (page-title + payment-title). */}
      <div className="page-title payment-title">
        <div>
          <h1><BarChart3 className="rel-title-icon" aria-hidden="true" />Relatórios Financeiros e Operacionais</h1>
          <p>Acompanhe os gastos, as faturas e a eficiência do processo.</p>
        </div>
        <BotaoFiltrar painel={painel} ativos={ativos} disabled={!opcoes} />
      </div>

      {opcoes && (
        <FilterPanel
          painel={painel}
          secoes={SECOES}
          opcoes={opcoes}
          onApply={aplicar}
          onClear={() => painel.setRascunho(RASCUNHO_PADRAO)}
        />
      )}

      {erro && (
        <div className="rf-card rf-error" role="alert">
          <p>{erro}</p>
          <button type="button" onClick={() => setTentativa((t) => t + 1)}>Tentar novamente</button>
        </div>
      )}
      {!dados && carregando && !erro && <p role="status" className="rf-status">Carregando relatório…</p>}

      {dados && (
        <div className={`rf-content${carregando ? ' is-loading' : ''}`} aria-busy={carregando}>
          {secao === 'visao-geral' && <>
            <KpiCards kpis={dados.kpis} />
            <div className="rf-charts">
              <EvolucaoCard dados={dados.evolucao} conta={filtros.conta} />
              <LocalCard itens={dados.porLocal.itens} nivel={dados.porLocal.nivel} conta={filtros.conta} contexto={contextoLocal} />
            </div>
          </>}
          {secao === 'evolucao' && <EvolucaoCard dados={dados.evolucao} conta={filtros.conta} comTabela />}
          {secao === 'localizacao' && <LocalCard itens={dados.porLocal.itens} nivel={dados.porLocal.nivel} conta={filtros.conta} contexto={contextoLocal} comTabela />}
          {!['visao-geral', 'evolucao', 'localizacao'].includes(secao) && (
            <section className="rf-card rf-wip">
              <secaoAtual.Icon size={40} aria-hidden={true} />
              <div className="resumo-heading">
                <h2>{secaoAtual.label}</h2>
                <p>Em construção</p>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
