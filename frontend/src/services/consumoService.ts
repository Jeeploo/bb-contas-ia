// Camada de serviço da tela "Relatórios de Consumo e Sustentabilidade".
// Bypass DEV ligado → mock filtrado. Bypass DEV desligado → API real (endpoints a definir).
import { isDevBypass } from '../config/devBypass';
import { request } from '../api/client';
import { AGENCIAS, CIDADES, ESTADOS, REGIOES } from '../mocks/relatoriosMock';
import {
  DIRETORIAS, LINHAS_CONSUMO, MESES_CONSUMO, SUPERINTENDENCIAS,
  type TipoConsumo, type Unidade,
} from '../mocks/consumoMock';
import {
  localDaAgencia, opcoesPeriodoDe,
  type OpcoesLocal, type OpcoesPeriodo, type Periodo,
} from './relatoriosService';

export type { TipoConsumo } from '../mocks/consumoMock';

export interface FiltrosConsumo {
  periodo: Periodo;
  regiao: string;
  estado: string;
  cidade: string;
  agencia: string;
  superintendencia: string; // pfx
  diretoria: string; // pfx
}

export type OpcoesConsumo = OpcoesPeriodo & OpcoesLocal & {
  superintendencias: Unidade[];
  diretorias: Unidade[];
};

export interface LinhaConsumo {
  prefixo: string;
  nome: string;
  ano: number;
  mes: number;
  /** Consumo de cada tipo (água m³, energia kWh, papel folhas, resíduos kg). */
  valores: Record<TipoConsumo, number>;
  superPfx: string;
  superNome: string;
  dirPfx: string;
  dirNome: string;
  atualizadoEm: string; // AAAA-MM-DD
  responsavel: string;
}

export interface RelatorioConsumo {
  totais: Record<TipoConsumo, number>;
  linhas: LinhaConsumo[];
}

// ---------------------------------------------------------------- API pública

export async function getOpcoesConsumo(): Promise<OpcoesConsumo> {
  if (isDevBypass()) {
    return {
      ...opcoesPeriodoDe(MESES_CONSUMO),
      regioes: REGIOES,
      estados: ESTADOS,
      cidades: CIDADES,
      agencias: AGENCIAS.map(({ id, nome, cidade }) => ({ id, nome, cidade })),
      superintendencias: SUPERINTENDENCIAS,
      diretorias: DIRETORIAS,
    };
  }
  // TODO: confirmar endpoint com o backend.
  return request<OpcoesConsumo>('/relatorios/consumo/filtros');
}

export async function getRelatorioConsumo(f: FiltrosConsumo): Promise<RelatorioConsumo> {
  if (isDevBypass()) return calcularMock(f);
  const p = new URLSearchParams();
  p.set('periodo_tipo', f.periodo.tipo);
  if (f.periodo.tipo === 'mes') p.set('mes', f.periodo.mes);
  if (f.periodo.tipo === 'ano') p.set('ano', f.periodo.ano);
  if (f.periodo.tipo === 'intervalo') { p.set('data_inicio', f.periodo.de); p.set('data_fim', f.periodo.ate); }
  (['regiao', 'estado', 'cidade', 'agencia', 'superintendencia', 'diretoria'] as const).forEach((k) => { if (f[k]) p.set(k, f[k]); });
  // TODO: confirmar endpoint, nomes dos parâmetros e formato de resposta com o backend.
  return request<RelatorioConsumo>('/relatorios/consumo?' + p.toString());
}

// ---------------------------------------------------------------- Mock

const superPorPfx = new Map(SUPERINTENDENCIAS.map((s) => [s.pfx, s.nome]));
const dirPorPfx = new Map(DIRETORIAS.map((d) => [d.pfx, d.nome]));
const nomeAgencia = new Map(AGENCIAS.map((a) => [a.id, a.nome.split(' — ')[1] ?? a.nome]));

function mesesDoPeriodo(p: Periodo): Set<string> {
  const ids = MESES_CONSUMO.map((m) => m.id);
  if (p.tipo === 'mes') return new Set(ids.filter((id) => id === p.mes));
  if (p.tipo === 'ano') return new Set(ids.filter((id) => id.startsWith(p.ano)));
  const de = p.de.slice(0, 7), ate = p.ate.slice(0, 7);
  return new Set(ids.filter((id) => id >= de && id <= ate));
}

function calcularMock(f: FiltrosConsumo): RelatorioConsumo {
  const meses = mesesDoPeriodo(f.periodo);
  const soma = { agua: 0, energia: 0, papel: 0, residuos: 0 };
  const linhas: LinhaConsumo[] = [];

  LINHAS_CONSUMO.forEach((l) => {
    if (!meses.has(l.mes)) return;
    const loc = localDaAgencia(l.agencia);
    if ((f.regiao && loc.regiao !== f.regiao) || (f.estado && loc.estado !== f.estado)
      || (f.cidade && loc.cidade !== f.cidade) || (f.agencia && loc.agencia !== f.agencia)
      || (f.superintendencia && l.superintendencia !== f.superintendencia)
      || (f.diretoria && l.diretoria !== f.diretoria)) return;

    soma.agua += l.agua; soma.energia += l.energia; soma.papel += l.papel; soma.residuos += l.residuos;
    const [ano, mes] = l.mes.split('-').map(Number);
    linhas.push({
      prefixo: l.agencia,
      nome: nomeAgencia.get(l.agencia) ?? l.agencia,
      ano, mes,
      valores: { agua: l.agua / 100, energia: l.energia, papel: l.papel, residuos: l.residuos / 100 },
      superPfx: l.superintendencia, superNome: superPorPfx.get(l.superintendencia) ?? '',
      dirPfx: l.diretoria, dirNome: dirPorPfx.get(l.diretoria) ?? '',
      atualizadoEm: l.atualizadoEm,
      responsavel: l.responsavel,
    });
  });

  return {
    totais: { agua: soma.agua / 100, energia: soma.energia, papel: soma.papel, residuos: soma.residuos / 100 },
    linhas,
  };
}
