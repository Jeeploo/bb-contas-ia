// Camada de serviço da tela "Relatórios Financeiros e Operacionais".
// Bypass DEV ligado → calcula a partir dos mocks (já filtrados).
// Bypass DEV desligado → chama a API real (endpoints ainda a definir no backend).
import { isDevBypass } from '../config/devBypass';
import { request } from '../api/client';
import {
  AGENCIAS, CIDADES, ESTADOS, MESES, MES_PADRAO, REGIOES, REGISTROS,
  type Agencia, type Cidade, type Estado, type Mes, type Regiao,
} from '../mocks/relatoriosMock';

// ---------------------------------------------------------------- Tipos

export type TipoConta = '' | 'energia' | 'agua';

/** Período codificado em texto (vai para a URL):
 *  "2026-10" = mês • "2026" = ano • "2026-03-01_2026-08-31" = intervalo. */
export type Periodo =
  | { tipo: 'mes'; mes: string }
  | { tipo: 'ano'; ano: string }
  | { tipo: 'intervalo'; de: string; ate: string };

export interface FiltrosFinanceiros {
  periodo: Periodo;
  regiao: string;
  estado: string;
  cidade: string;
  agencia: string;
  conta: TipoConta;
}

/** Opções de período (compartilhadas pelas páginas de Relatórios). */
export interface OpcoesPeriodo {
  meses: Mes[];
  anos: string[];
  /** Limites para o intervalo personalizado (AAAA-MM-DD). */
  dataMin: string;
  dataMax: string;
}

/** Opções da cascata Região → Estado → Cidade → Agência. */
export interface OpcoesLocal {
  regioes: Regiao[];
  estados: Estado[];
  cidades: Cidade[];
  agencias: Pick<Agencia, 'id' | 'nome' | 'cidade'>[];
}

export type OpcoesFiltroFinanceiro = OpcoesPeriodo & OpcoesLocal;

export interface Indicador {
  valor: number;
  anterior: number | null;
  /** Variação percentual vs. período anterior (ex.: -5.2). null quando não há período anterior. */
  variacao: number | null;
}

export interface PontoEvolucao {
  mes: string;
  rotulo: string;
  energia: number;
  agua: number;
  total: number;
  faturas: number;
}

export type NivelLocal = 'regiao' | 'estado' | 'cidade' | 'agencia';

export interface ItemLocal {
  id: string;
  nome: string;
  energia: number;
  agua: number;
  total: number;
  faturas: number;
}

export interface RelatorioFinanceiro {
  /** null = tipo de conta excluído pelo filtro "Tipo de conta". */
  kpis: { total: Indicador; energia: Indicador | null; agua: Indicador | null; faturas: Indicador };
  evolucao: PontoEvolucao[];
  porLocal: { nivel: NivelLocal; itens: ItemLocal[] };
}

// ---------------------------------------------------------------- Período

export const PERIODO_PADRAO: Periodo = { tipo: 'mes', mes: MES_PADRAO };

export const FILTROS_PADRAO: FiltrosFinanceiros = {
  periodo: PERIODO_PADRAO, regiao: '', estado: '', cidade: '', agencia: '', conta: '',
};

export function periodoParaTexto(p: Periodo): string {
  return p.tipo === 'mes' ? p.mes : p.tipo === 'ano' ? p.ano : `${p.de}_${p.ate}`;
}

export function textoParaPeriodo(s: string | null): Periodo | null {
  if (!s) return null;
  if (/^\d{4}-\d{2}$/.test(s)) return { tipo: 'mes', mes: s };
  if (/^\d{4}$/.test(s)) return { tipo: 'ano', ano: s };
  const m = /^(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})$/.exec(s);
  return m ? { tipo: 'intervalo', de: m[1], ate: m[2] } : null;
}

export const mesmoPeriodo = (a: Periodo, b: Periodo) => periodoParaTexto(a) === periodoParaTexto(b);

/** Período válido para as opções disponíveis? (mês existente, ano existente, intervalo dentro dos limites e em ordem) */
export function periodoValido(p: Periodo, o: OpcoesPeriodo): boolean {
  if (p.tipo === 'mes') return o.meses.some((m) => m.id === p.mes);
  if (p.tipo === 'ano') return o.anos.includes(p.ano);
  return !!p.de && !!p.ate && p.de <= p.ate && p.de >= o.dataMin && p.ate <= o.dataMax;
}

// ---------------------------------------------------------------- Cascata

/** Garante Região → Estado → Cidade → Agência coerentes; filhos incoerentes viram "Todos". */
export function normalizarLocal<T extends Pick<FiltrosFinanceiros, 'regiao' | 'estado' | 'cidade' | 'agencia'>>(f: T, o: OpcoesLocal): T {
  const regiao = o.regioes.some((r) => r.id === f.regiao) ? f.regiao : '';
  const estado = o.estados.some((e) => e.id === f.estado && (!regiao || e.regiao === regiao)) ? f.estado : '';
  const cidadesOk = opcoesCidade(o, regiao, estado);
  const cidade = cidadesOk.some((c) => c.id === f.cidade) ? f.cidade : '';
  const agencia = opcoesAgencia(o, regiao, estado, cidade).some((a) => a.id === f.agencia) ? f.agencia : '';
  return { ...f, regiao, estado, cidade, agencia };
}

export const opcoesEstado = (o: OpcoesLocal, regiao: string) =>
  o.estados.filter((e) => !regiao || e.regiao === regiao);

export function opcoesCidade(o: OpcoesLocal, regiao: string, estado: string) {
  const ufs = new Set(opcoesEstado(o, regiao).map((e) => e.id));
  return o.cidades.filter((c) => (estado ? c.estado === estado : ufs.has(c.estado)));
}

export function opcoesAgencia(o: OpcoesLocal, regiao: string, estado: string, cidade: string) {
  const cidades = new Set(opcoesCidade(o, regiao, estado).map((c) => c.id));
  return o.agencias.filter((a) => (cidade ? a.cidade === cidade : cidades.has(a.cidade)));
}

// ---------------------------------------------------------------- API pública

/** Monta as opções de período a partir de uma lista de meses. */
export function opcoesPeriodoDe(meses: Mes[]): OpcoesPeriodo {
  const ultimo = meses[meses.length - 1].id;
  const [a, m] = ultimo.split('-').map(Number);
  return {
    meses,
    anos: [...new Set(meses.map((x) => x.id.slice(0, 4)))],
    dataMin: `${meses[0].id}-01`,
    dataMax: `${ultimo}-${String(new Date(a, m, 0).getDate()).padStart(2, '0')}`,
  };
}

export async function getOpcoesFiltroFinanceiro(): Promise<OpcoesFiltroFinanceiro> {
  if (isDevBypass()) {
    return {
      ...opcoesPeriodoDe(MESES),
      regioes: REGIOES,
      estados: ESTADOS,
      cidades: CIDADES,
      agencias: AGENCIAS.map(({ id, nome, cidade }) => ({ id, nome, cidade })),
    };
  }
  // TODO: confirmar endpoint com o backend.
  return request<OpcoesFiltroFinanceiro>('/relatorios/financeiros/filtros');
}

export async function getRelatorioFinanceiro(filtros: FiltrosFinanceiros): Promise<RelatorioFinanceiro> {
  if (isDevBypass()) return calcularMock(filtros);
  const p = new URLSearchParams();
  const per = filtros.periodo;
  p.set('periodo_tipo', per.tipo);
  if (per.tipo === 'mes') p.set('mes', per.mes);
  if (per.tipo === 'ano') p.set('ano', per.ano);
  if (per.tipo === 'intervalo') { p.set('data_inicio', per.de); p.set('data_fim', per.ate); }
  (['regiao', 'estado', 'cidade', 'agencia', 'conta'] as const).forEach((k) => { if (filtros[k]) p.set(k, filtros[k]); });
  // TODO: confirmar endpoint, nomes dos parâmetros e formato de resposta com o backend.
  return request<RelatorioFinanceiro>('/relatorios/financeiros?' + p.toString());
}

// ---------------------------------------------------------------- Mock

const estadoDaCidade = new Map(CIDADES.map((c) => [c.id, c.estado]));
const regiaoDoEstado = new Map(ESTADOS.map((e) => [e.id, e.regiao]));
const agenciaPorId = new Map(AGENCIAS.map((a) => [a.id, a]));

export function localDaAgencia(id: string) {
  const cidade = agenciaPorId.get(id)!.cidade;
  const estado = estadoDaCidade.get(cidade)!;
  return { agencia: id, cidade, estado, regiao: regiaoDoEstado.get(estado)! };
}

function indicador(atual: number, anterior: number | null): Indicador {
  return {
    valor: atual,
    anterior,
    variacao: anterior ? Math.round(((atual - anterior) / anterior) * 1000) / 10 : null,
  };
}

/** Índices (em MESES) dos meses cobertos pelo período. */
function indicesDoPeriodo(p: Periodo): number[] {
  const ids = MESES.map((m) => m.id);
  if (p.tipo === 'mes') return [ids.indexOf(p.mes)].filter((i) => i >= 0);
  if (p.tipo === 'ano') return ids.flatMap((id, i) => (id.startsWith(p.ano) ? [i] : []));
  const de = p.de.slice(0, 7), ate = p.ate.slice(0, 7);
  return ids.flatMap((id, i) => (id >= de && id <= ate ? [i] : []));
}

function calcularMock(f: FiltrosFinanceiros): RelatorioFinanceiro {
  const registros = REGISTROS.filter((r) => {
    const loc = localDaAgencia(r.agencia);
    return (!f.regiao || loc.regiao === f.regiao)
      && (!f.estado || loc.estado === f.estado)
      && (!f.cidade || loc.cidade === f.cidade)
      && (!f.agencia || loc.agencia === f.agencia);
  });

  const usaEnergia = f.conta !== 'agua';
  const usaAgua = f.conta !== 'energia';

  const somaMeses = (idx: number[]) => {
    const meses = new Set(idx.map((i) => MESES[i].id));
    let e = 0, a = 0, fat = 0;
    registros.forEach((r) => { if (meses.has(r.mes)) { e += r.energiaCent; a += r.aguaCent; fat += r.faturas; } });
    return {
      energia: e / 100, agua: a / 100,
      total: ((usaEnergia ? e : 0) + (usaAgua ? a : 0)) / 100,
      faturas: fat,
    };
  };

  let idx = indicesDoPeriodo(f.periodo);
  if (!idx.length) idx = [MESES.length - 1];
  const primeiro = idx[0];
  const ultimo = idx[idx.length - 1];
  // Período anterior: mesma quantidade de meses imediatamente antes.
  const idxAnterior = primeiro - idx.length >= 0 ? idx.map((i) => i - idx.length) : null;

  const atual = somaMeses(idx);
  const anterior = idxAnterior ? somaMeses(idxAnterior) : null;

  // Gráfico de evolução: os meses do período; se forem menos de 6, os 6 meses até o fim do período.
  const inicioJanela = idx.length >= 6 ? primeiro : Math.max(0, ultimo - 5);
  const evolucao = MESES.slice(inicioJanela, ultimo + 1).map((m, k) => ({
    mes: m.id, rotulo: m.curto, ...somaMeses([inicioJanela + k]),
  }));

  // Nível do gráfico por localização: um abaixo do filtro mais específico.
  const nivel: NivelLocal = f.cidade || f.agencia ? 'agencia' : f.estado ? 'cidade' : f.regiao ? 'estado' : 'regiao';
  const nomes: Record<NivelLocal, Map<string, string>> = {
    regiao: new Map(REGIOES.map((r) => [r.id, r.nome])),
    estado: new Map(ESTADOS.map((e) => [e.id, e.nome])),
    cidade: new Map(CIDADES.map((c) => [c.id, c.nome])),
    agencia: new Map(AGENCIAS.map((a) => [a.id, a.nome])),
  };
  const mesesPeriodo = new Set(idx.map((i) => MESES[i].id));
  const grupos = new Map<string, { e: number; a: number; fat: number }>();
  registros.forEach((r) => {
    if (!mesesPeriodo.has(r.mes)) return;
    const chave = localDaAgencia(r.agencia)[nivel];
    const g = grupos.get(chave) ?? { e: 0, a: 0, fat: 0 };
    g.e += r.energiaCent; g.a += r.aguaCent; g.fat += r.faturas;
    grupos.set(chave, g);
  });
  const itens = [...grupos.entries()]
    .map(([id, g]) => ({
      id, nome: nomes[nivel].get(id) ?? id,
      energia: g.e / 100, agua: g.a / 100,
      total: ((usaEnergia ? g.e : 0) + (usaAgua ? g.a : 0)) / 100,
      faturas: g.fat,
    }))
    .sort((a, b) => b.total - a.total);

  return {
    kpis: {
      total: indicador(atual.total, anterior?.total ?? null),
      energia: usaEnergia ? indicador(atual.energia, anterior?.energia ?? null) : null,
      agua: usaAgua ? indicador(atual.agua, anterior?.agua ?? null) : null,
      faturas: indicador(atual.faturas, anterior?.faturas ?? null),
    },
    evolucao,
    porLocal: { nivel, itens },
  };
}
