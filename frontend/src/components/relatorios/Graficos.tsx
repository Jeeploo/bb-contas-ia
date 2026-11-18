import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { MapPin, TrendingUp } from 'lucide-react';
import type { ItemLocal, NivelLocal, PontoEvolucao, TipoConta } from '../../services/relatoriosService';
import { brl, brlCompacto, inteiro } from './format';

const ENERGIA = '#0A3A8C';
const AGUA = '#1EA7F5';
const EIXO = { fill: '#6a7a8f', fontSize: 12 }; // cor/tamanho de .resumo-campo-texto span

const traco = (mostrar: boolean, v: number) => (mostrar ? brl(v) : '—');

// ------------------------------------------------------------ Evolução

interface TooltipProps { active?: boolean; label?: string; payload?: { dataKey?: string | number; value?: number }[] }

function EvolucaoTooltip({ active, label, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const v = (k: string) => payload.find((p) => p.dataKey === k)?.value;
  const e = v('energia'), a = v('agua');
  return (
    <div className="rf-tip">
      <strong>{label}</strong>
      {e !== undefined && <span><i style={{ background: ENERGIA }} />Energia: {brl(e)}</span>}
      {a !== undefined && <span><i style={{ background: AGUA }} />Água: {brl(a)}</span>}
      {e !== undefined && a !== undefined && <span className="rf-tip__total">Total: {brl(e + a)}</span>}
    </div>
  );
}

export function EvolucaoCard({ dados, conta, comTabela = false }: { dados: PontoEvolucao[]; conta: TipoConta; comTabela?: boolean }) {
  const comEnergia = conta !== 'agua';
  const comAgua = conta !== 'energia';
  return (
    <section className="rf-card rf-chart">
      <header className="rf-chart__head resumo-heading">
        <h2><TrendingUp size={20} aria-hidden="true" /> Evolução das despesas</h2>
        <ul className="rf-legend" aria-label="Legenda">
          {comEnergia && <li><i style={{ background: ENERGIA }} />Energia</li>}
          {comAgua && <li><i style={{ background: AGUA }} />Água</li>}
        </ul>
      </header>
      <div className="rf-chart__plot" role="img" aria-label={`Gráfico de linhas: gastos de ${dados[0]?.rotulo} a ${dados.at(-1)?.rotulo}`}>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={dados} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="rf-g-energia" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={ENERGIA} stopOpacity={0.14} />
                <stop offset="100%" stopColor={ENERGIA} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#EEF2F7" vertical={false} />
            <XAxis dataKey="rotulo" tickLine={false} axisLine={false} tick={EIXO} />
            <YAxis tickFormatter={brlCompacto} tickLine={false} axisLine={false} width={76} tick={EIXO} />
            <Tooltip content={<EvolucaoTooltip />} cursor={{ stroke: '#C9D4E5', strokeDasharray: '4 4' }} />
            {comEnergia && <Area type="monotone" dataKey="energia" name="Energia" stroke={ENERGIA} strokeWidth={2.5} fill="url(#rf-g-energia)" dot={{ r: 4, fill: ENERGIA, strokeWidth: 0 }} activeDot={{ r: 6 }} />}
            {comAgua && <Area type="monotone" dataKey="agua" name="Água" stroke={AGUA} strokeWidth={2.5} fill="none" dot={{ r: 4, fill: AGUA, strokeWidth: 0 }} activeDot={{ r: 6 }} />}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {comTabela && (
        <div className="rf-table-wrap">
          <table className="rf-table">
            <caption className="rf-sr">Gastos mês a mês</caption>
            <thead><tr><th scope="col">Mês</th><th scope="col">Energia</th><th scope="col">Água</th><th scope="col">Total</th><th scope="col">Faturas</th></tr></thead>
            <tbody>
              {dados.map((d) => (
                <tr key={d.mes}><th scope="row">{d.rotulo}</th><td>{traco(comEnergia, d.energia)}</td><td>{traco(comAgua, d.agua)}</td><td><strong>{brl(d.total)}</strong></td><td>{inteiro(d.faturas)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ------------------------------------------------------------ Por localização

const NIVEL_TITULO: Record<NivelLocal, string> = {
  regiao: 'Região', estado: 'Estado', cidade: 'Cidade', agencia: 'Agência',
};

/** Do azul mais escuro (maior) ao mais claro (menor). */
function tom(i: number, n: number) {
  const ini = [0x0a, 0x3a, 0x8c];
  const fim = [0xa9, 0xc8, 0xf2];
  const t = n <= 1 ? 0 : i / (n - 1);
  return `rgb(${ini.map((c, k) => Math.round(c + (fim[k] - c) * t)).join(',')})`;
}

export function LocalCard({ itens, nivel, conta, contexto, comTabela = false }: { itens: ItemLocal[]; nivel: NivelLocal; conta: TipoConta; contexto?: string; comTabela?: boolean }) {
  const total = itens.reduce((s, i) => s + i.total, 0);
  const altura = Math.max(140, itens.length * 48 + 16);
  const nomeNivel = NIVEL_TITULO[nivel].toLowerCase();
  return (
    <section className="rf-card rf-chart">
      <header className="rf-chart__head resumo-heading">
        <h2><MapPin size={20} aria-hidden="true" /> Gastos por região</h2>
        <p className="rf-chart__ctx">Por {nomeNivel}{contexto ? ` · ${contexto}` : ''}</p>
      </header>
      {!itens.length ? <p className="rf-empty">Sem dados para os filtros selecionados.</p> : (
        <div className="rf-chart__plot" role="img" aria-label={`Barras: gasto por ${nomeNivel}. ${itens.map((i) => `${i.nome}: ${brl(i.total)}`).join('; ')}`}>
          <ResponsiveContainer width="100%" height={altura}>
            <BarChart data={itens} layout="vertical" margin={{ top: 4, right: 128, left: 0, bottom: 4 }} barCategoryGap={10}>
              <XAxis type="number" hide domain={[0, 'dataMax']} />
              <YAxis type="category" dataKey="nome" width={nivel === 'agencia' ? 190 : 110} tickLine={false} axisLine={false} tick={{ fill: '#183967', fontSize: 14, fontWeight: 700 }} />
              <Tooltip cursor={{ fill: 'rgba(10,58,140,0.05)' }} formatter={(v: number) => [brl(v), 'Gasto']} />
              <Bar dataKey="total" radius={[0, 6, 6, 0]} maxBarSize={28}>
                {itens.map((it, i) => <Cell key={it.id} fill={tom(i, itens.length)} />)}
                <LabelList dataKey="total" position="right" formatter={(v: number) => brl(v)} style={{ fill: '#183967', fontSize: 14, fontWeight: 700 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {comTabela && itens.length > 0 && (
        <div className="rf-table-wrap">
          <table className="rf-table">
            <caption className="rf-sr">Gastos por {nomeNivel}</caption>
            <thead><tr><th scope="col">{NIVEL_TITULO[nivel]}</th><th scope="col">Energia</th><th scope="col">Água</th><th scope="col">Total</th><th scope="col">% do total</th><th scope="col">Faturas</th></tr></thead>
            <tbody>
              {itens.map((it) => (
                <tr key={it.id}>
                  <th scope="row">{it.nome}</th><td>{traco(conta !== 'agua', it.energia)}</td><td>{traco(conta !== 'energia', it.agua)}</td><td><strong>{brl(it.total)}</strong></td>
                  <td>{total ? `${((it.total / total) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%` : '—'}</td><td>{inteiro(it.faturas)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
