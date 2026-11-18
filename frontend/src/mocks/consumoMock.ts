// Dados FICTÍCIOS para a tela "Relatórios de Consumo e Sustentabilidade".
// Usados apenas com o bypass DEV ligado (ver services/consumoService.ts).
// Mesmas regiões/estados/cidades/agências de relatoriosMock.ts.
//
// Água e resíduos ficam em CENTÉSIMOS (m³ e kg) para somas exatas. Os totais
// nacionais de cada mês são fixos e distribuídos entre as agências; sem filtro,
// em Out/2026: água 759,87 m³ • energia 1.726.450 kWh • papel 8.420 folhas • resíduos 284,32 kg.
import { AGENCIAS, CIDADES, ESTADOS, MESES, distribuir, type Mes } from './relatoriosMock';

export type TipoConsumo = 'agua' | 'energia' | 'papel' | 'residuos';

export interface Unidade { pfx: string; nome: string }

export const SUPERINTENDENCIAS: Unidade[] = [
  { pfx: '8501', nome: 'Super. Pernambuco' },
  { pfx: '8502', nome: 'Super. Bahia' },
  { pfx: '8503', nome: 'Super. Ceará' },
  { pfx: '8601', nome: 'Super. São Paulo' },
  { pfx: '8602', nome: 'Super. Rio de Janeiro' },
  { pfx: '8603', nome: 'Super. Minas Gerais' },
  { pfx: '8701', nome: 'Super. Sul' },
  { pfx: '8801', nome: 'Super. Centro-Oeste' },
  { pfx: '8901', nome: 'Super. Norte' },
];

export const DIRETORIAS: Unidade[] = [
  { pfx: '9601', nome: 'Diretoria Varejo Norte-Nordeste' },
  { pfx: '9602', nome: 'Diretoria Varejo Sudeste' },
  { pfx: '9603', nome: 'Diretoria Varejo Sul e Centro-Oeste' },
];

const SUPER_POR_UF: Record<string, string> = {
  PE: '8501', BA: '8502', CE: '8503', SP: '8601', RJ: '8602', MG: '8603',
  PR: '8701', RS: '8701', SC: '8701', DF: '8801', GO: '8801', AM: '8901', PA: '8901',
};
const DIRETORIA_POR_REGIAO: Record<string, string> = {
  nordeste: '9601', norte: '9601', sudeste: '9602', sul: '9603', 'centro-oeste': '9603',
};

// Um responsável por agência (fictícios). 9090 = Marcos Gomes.
const RESPONSAVEIS: Record<string, string> = {
  '9090': 'Marcos Gomes', '1234': 'Ana Paula Lima', '2210': 'José Ricardo Alves', '3001': 'Carla Menezes',
  '3002': 'Rafael Souza', '3010': 'Juliana Prado', '4001': 'Fernando Rocha', '4002': 'Patrícia Nunes',
  '5001': 'Bruno Carvalho', '5002': 'Luciana Teixeira', '5010': 'Diego Martins', '5101': 'Renata Costa',
  '5201': 'Thiago Mendes', '6001': 'Camila Ribeiro', '6101': 'Eduardo Schmidt', '6201': 'Mariana Duarte',
  '7001': 'Gustavo Pires', '7002': 'Aline Barros', '7101': 'Rodrigo Freitas', '8001': 'Larissa Moraes',
  '8101': 'Paulo Henrique Dias',
};

/** Mai/2026 a Out/2026. */
export const MESES_CONSUMO: Mes[] = MESES.slice(-6);

// Totais nacionais por mês (ordem de MESES_CONSUMO).
const TOTAIS: Record<TipoConsumo, number[]> = {
  agua: [72310, 73845, 77120, 79064, 79070, 75987], // centésimos de m³
  energia: [1638200, 1702330, 1768410, 1810950, 1821150, 1726450], // kWh
  papel: [7910, 8045, 8230, 8310, 8380, 8420], // folhas
  residuos: [27105, 27630, 28890, 29410, 29055, 28432], // centésimos de kg
};
const FASE: Record<TipoConsumo, number> = { agua: 0.5, energia: 1.5, papel: 2.5, residuos: 3.5 };

export interface LinhaConsumoMock {
  agencia: string;
  mes: string; // AAAA-MM
  /** Água e resíduos em centésimos; energia e papel em unidades. */
  agua: number;
  energia: number;
  papel: number;
  residuos: number;
  superintendencia: string; // pfx
  diretoria: string; // pfx
  atualizadoEm: string; // AAAA-MM-DD
  responsavel: string;
}

const ufDaCidade = new Map(CIDADES.map((c) => [c.id, c.estado]));
const regiaoDaUf = new Map(ESTADOS.map((e) => [e.id, e.regiao]));
const ruido = (a: number, m: number, s: number) => 1 + 0.07 * Math.sin(a * 7.13 + m * 3.71 + s);

function gerar(): LinhaConsumoMock[] {
  const linhas: LinhaConsumoMock[] = [];
  MESES_CONSUMO.forEach((mes, m) => {
    const por = Object.fromEntries(
      (Object.keys(TOTAIS) as TipoConsumo[]).map((t) => [t, distribuir(TOTAIS[t][m], AGENCIAS.map((ag, a) => ag.peso * ruido(a, m, FASE[t])))]),
    ) as Record<TipoConsumo, number[]>;
    // Atualização: início do mês seguinte (dia 3 a 12 conforme a agência).
    const [ano, mm] = mes.id.split('-').map(Number);
    const prox = mm === 12 ? `${ano + 1}-01` : `${ano}-${String(mm + 1).padStart(2, '0')}`;
    AGENCIAS.forEach((ag, a) => {
      const uf = ufDaCidade.get(ag.cidade)!;
      linhas.push({
        agencia: ag.id,
        mes: mes.id,
        agua: por.agua[a], energia: por.energia[a], papel: por.papel[a], residuos: por.residuos[a],
        superintendencia: SUPER_POR_UF[uf],
        diretoria: DIRETORIA_POR_REGIAO[regiaoDaUf.get(uf)!],
        atualizadoEm: `${prox}-${String(3 + (a % 10)).padStart(2, '0')}`,
        responsavel: RESPONSAVEIS[ag.id] ?? '—',
      });
    });
  });
  return linhas;
}

export const LINHAS_CONSUMO: LinhaConsumoMock[] = gerar();
