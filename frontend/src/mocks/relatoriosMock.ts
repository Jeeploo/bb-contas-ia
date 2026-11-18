// Dados FICTÍCIOS para a tela "Relatórios Financeiros e Operacionais".
// Usados apenas com o bypass DEV ligado (ver services/relatoriosService.ts).
//
// Valores monetários ficam em CENTAVOS (inteiros) para que as somas sejam
// exatas. Os totais nacionais de cada mês são fixos e distribuídos entre as
// agências por peso, de modo que a visão geral sem filtro em Out/2026 dá:
//   energia R$ 1.726.450,00 (−5,2% vs. Set) • água R$ 759.870,00 (−3,9%)
//   faturas 8.420 (+6,1%)

export interface Regiao { id: string; nome: string }
export interface Estado { id: string; nome: string; regiao: string }
export interface Cidade { id: string; nome: string; estado: string }
export interface Agencia { id: string; nome: string; cidade: string; peso: number }
export interface Mes { id: string; curto: string; longo: string }
export interface RegistroMensal {
  agencia: string;
  mes: string;
  energiaCent: number;
  aguaCent: number;
  faturas: number;
}

export const REGIOES: Regiao[] = [
  { id: 'nordeste', nome: 'Nordeste' },
  { id: 'sudeste', nome: 'Sudeste' },
  { id: 'sul', nome: 'Sul' },
  { id: 'centro-oeste', nome: 'Centro-Oeste' },
  { id: 'norte', nome: 'Norte' },
];

export const ESTADOS: Estado[] = [
  { id: 'PE', nome: 'Pernambuco', regiao: 'nordeste' },
  { id: 'BA', nome: 'Bahia', regiao: 'nordeste' },
  { id: 'CE', nome: 'Ceará', regiao: 'nordeste' },
  { id: 'SP', nome: 'São Paulo', regiao: 'sudeste' },
  { id: 'RJ', nome: 'Rio de Janeiro', regiao: 'sudeste' },
  { id: 'MG', nome: 'Minas Gerais', regiao: 'sudeste' },
  { id: 'PR', nome: 'Paraná', regiao: 'sul' },
  { id: 'RS', nome: 'Rio Grande do Sul', regiao: 'sul' },
  { id: 'SC', nome: 'Santa Catarina', regiao: 'sul' },
  { id: 'DF', nome: 'Distrito Federal', regiao: 'centro-oeste' },
  { id: 'GO', nome: 'Goiás', regiao: 'centro-oeste' },
  { id: 'AM', nome: 'Amazonas', regiao: 'norte' },
  { id: 'PA', nome: 'Pará', regiao: 'norte' },
];

export const CIDADES: Cidade[] = [
  { id: 'recife', nome: 'Recife', estado: 'PE' },
  { id: 'caruaru', nome: 'Caruaru', estado: 'PE' },
  { id: 'salvador', nome: 'Salvador', estado: 'BA' },
  { id: 'feira-de-santana', nome: 'Feira de Santana', estado: 'BA' },
  { id: 'fortaleza', nome: 'Fortaleza', estado: 'CE' },
  { id: 'sao-paulo', nome: 'São Paulo', estado: 'SP' },
  { id: 'campinas', nome: 'Campinas', estado: 'SP' },
  { id: 'rio-de-janeiro', nome: 'Rio de Janeiro', estado: 'RJ' },
  { id: 'belo-horizonte', nome: 'Belo Horizonte', estado: 'MG' },
  { id: 'curitiba', nome: 'Curitiba', estado: 'PR' },
  { id: 'porto-alegre', nome: 'Porto Alegre', estado: 'RS' },
  { id: 'florianopolis', nome: 'Florianópolis', estado: 'SC' },
  { id: 'brasilia', nome: 'Brasília', estado: 'DF' },
  { id: 'goiania', nome: 'Goiânia', estado: 'GO' },
  { id: 'manaus', nome: 'Manaus', estado: 'AM' },
  { id: 'belem', nome: 'Belém', estado: 'PA' },
];

// peso = participação relativa nos gastos (Nordeste 34, Sudeste 30, Sul 16, Centro-Oeste 12, Norte 8)
export const AGENCIAS: Agencia[] = [
  { id: '9090', nome: '9090 — Recife Centro', cidade: 'recife', peso: 4.5 },
  { id: '1234', nome: '1234 — Recife Boa Vista', cidade: 'recife', peso: 4.0 },
  { id: '2210', nome: '2210 — Caruaru', cidade: 'caruaru', peso: 2.5 },
  { id: '3001', nome: '3001 — Salvador Comércio', cidade: 'salvador', peso: 5.0 },
  { id: '3002', nome: '3002 — Salvador Barra', cidade: 'salvador', peso: 4.0 },
  { id: '3010', nome: '3010 — Feira de Santana', cidade: 'feira-de-santana', peso: 3.0 },
  { id: '4001', nome: '4001 — Fortaleza Centro', cidade: 'fortaleza', peso: 6.0 },
  { id: '4002', nome: '4002 — Fortaleza Aldeota', cidade: 'fortaleza', peso: 5.0 },
  { id: '5001', nome: '5001 — São Paulo Paulista', cidade: 'sao-paulo', peso: 7.0 },
  { id: '5002', nome: '5002 — São Paulo Pinheiros', cidade: 'sao-paulo', peso: 5.5 },
  { id: '5010', nome: '5010 — Campinas', cidade: 'campinas', peso: 3.5 },
  { id: '5101', nome: '5101 — Rio de Janeiro Centro', cidade: 'rio-de-janeiro', peso: 7.5 },
  { id: '5201', nome: '5201 — Belo Horizonte', cidade: 'belo-horizonte', peso: 6.5 },
  { id: '6001', nome: '6001 — Curitiba', cidade: 'curitiba', peso: 6.0 },
  { id: '6101', nome: '6101 — Porto Alegre', cidade: 'porto-alegre', peso: 6.0 },
  { id: '6201', nome: '6201 — Florianópolis', cidade: 'florianopolis', peso: 4.0 },
  { id: '7001', nome: '7001 — Brasília Esplanada', cidade: 'brasilia', peso: 5.0 },
  { id: '7002', nome: '7002 — Brasília Asa Sul', cidade: 'brasilia', peso: 3.5 },
  { id: '7101', nome: '7101 — Goiânia', cidade: 'goiania', peso: 3.5 },
  { id: '8001', nome: '8001 — Manaus', cidade: 'manaus', peso: 4.5 },
  { id: '8101', nome: '8101 — Belém', cidade: 'belem', peso: 3.5 },
];

const NOMES_MES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

/** Jan/2025 a Out/2026 (22 meses). */
export const MESES: Mes[] = Array.from({ length: 22 }, (_, i) => {
  const ano = 2025 + Math.floor(i / 12);
  const m = i % 12;
  return {
    id: `${ano}-${String(m + 1).padStart(2, '0')}`,
    curto: `${NOMES_MES[m]}/${String(ano).slice(2)}`,
    longo: `${NOMES_MES[m]}/${ano}`,
  };
});

export const MES_PADRAO = '2026-10';

// Totais nacionais por mês, na mesma ordem de MESES (energia/água em centavos).
// Jan–Nov/2025 são gerados; Dez/2025–Out/2026 são fixos (Set e Out definem as variações exibidas).
const GERADOS = 11;
const gerado = (base: number, amp: number, fase: number) =>
  Array.from({ length: GERADOS }, (_, i) => Math.round(base + amp * Math.sin(i * 0.7 + fase)));
const TOTAIS_ENERGIA = [
  ...gerado(162_000_000, 7_500_000, 0),
  170510000, 174288000, 169845000, 166572000, 163190000, 161230000, 168894000, 175421000, 180253000, 182114979, 172645000,
];
const TOTAIS_AGUA = [
  ...gerado(71_000_000, 3_500_000, 1),
  74231000, 76894000, 75120000, 72886000, 70933000, 70245000, 72830000, 76192000, 78104000, 79070760, 75987000,
];
const TOTAIS_FATURAS = [
  ...gerado(6_700, 180, 2),
  7120, 7050, 7180, 7260, 7340, 7410, 7580, 7720, 7860, 7936, 8420,
];

/** Divide `total` (inteiro) proporcionalmente aos pesos, sem perder unidades no arredondamento. */
export function distribuir(total: number, pesos: number[]): number[] {
  const soma = pesos.reduce((a, b) => a + b, 0);
  const brutos = pesos.map((p) => (total * p) / soma);
  const base = brutos.map(Math.floor);
  let resto = total - base.reduce((a, b) => a + b, 0);
  const ordem = brutos.map((b, i) => [b - base[i], i] as const).sort((a, b) => b[0] - a[0]);
  for (let k = 0; resto > 0; k++, resto--) base[ordem[k % ordem.length][1]]++;
  return base;
}

/** Variação determinística (±6%) para cada agência/mês não ficar idêntica. */
const ruido = (a: number, m: number, s: number) => 1 + 0.06 * Math.sin(a * 12.9898 + m * 78.233 + s);

function gerarRegistros(): RegistroMensal[] {
  const registros: RegistroMensal[] = [];
  MESES.forEach((mes, m) => {
    const energia = distribuir(TOTAIS_ENERGIA[m], AGENCIAS.map((ag, a) => ag.peso * ruido(a, m, 0)));
    // Água pesa um pouco diferente da energia em cada agência.
    const agua = distribuir(TOTAIS_AGUA[m], AGENCIAS.map((ag, a) => ag.peso * (0.8 + (a % 5) / 10) * ruido(a, m, 1)));
    const faturas = distribuir(TOTAIS_FATURAS[m], AGENCIAS.map((ag, a) => ag.peso * ruido(a, m, 2)));
    AGENCIAS.forEach((ag, a) => {
      registros.push({ agencia: ag.id, mes: mes.id, energiaCent: energia[a], aguaCent: agua[a], faturas: faturas[a] });
    });
  });
  return registros;
}

export const REGISTROS: RegistroMensal[] = gerarRegistros();
