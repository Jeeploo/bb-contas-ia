const brlFmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const intFmt = new Intl.NumberFormat('pt-BR');
const dec1 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const brl = (v: number) => brlFmt.format(v);
export const inteiro = (v: number) => intFmt.format(v);
export const percentual = (v: number) => `${v > 0 ? '+' : ''}${dec1.format(v)}%`;

/** Eixo dos gráficos: "R$ 400 mil", "R$ 1,2 mi". */
export function brlCompacto(v: number) {
  if (Math.abs(v) >= 1_000_000) return `R$ ${dec1.format(v / 1_000_000).replace(/,0$/, '')} mi`;
  if (Math.abs(v) >= 1_000) return `R$ ${intFmt.format(Math.round(v / 1_000))} mil`;
  return brl(v);
}
