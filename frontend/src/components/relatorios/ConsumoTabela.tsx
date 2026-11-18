import { useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, FileSearch } from 'lucide-react';
import type { LinhaConsumo, TipoConsumo } from '../../services/consumoService';
import { inteiro } from './format';

const POR_PAGINA = 10;

export const UNIDADE: Record<TipoConsumo, string> = { agua: 'm³', energia: 'kWh', papel: 'folhas', residuos: 'kg' };
const dec2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
/** Água e resíduos com 2 casas; energia e papel inteiros. */
export const formatarConsumo = (tipo: TipoConsumo, v: number) => (tipo === 'agua' || tipo === 'residuos' ? dec2.format(v) : inteiro(v));

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const data = (iso: string) => iso.split('-').reverse().join('/');

type Chave = 'prefixo' | 'nome' | 'ano' | 'mes' | 'consumo' | 'superPfx' | 'superNome' | 'dirPfx' | 'dirNome' | 'atualizadoEm' | 'responsavel';

const collator = new Intl.Collator('pt-BR', { numeric: true, sensitivity: 'base' });

export function ConsumoTabela({ linhas, tipo }: { linhas: LinhaConsumo[]; tipo: TipoConsumo }) {
  const [ordem, setOrdem] = useState<{ chave: Chave; asc: boolean }>({ chave: 'prefixo', asc: true });
  const [pagina, setPagina] = useState(1);

  const colunas: { chave: Chave; titulo: string; numero?: boolean }[] = [
    { chave: 'prefixo', titulo: 'Prefixo' },
    { chave: 'nome', titulo: 'Nome' },
    { chave: 'ano', titulo: 'Ano', numero: true },
    { chave: 'mes', titulo: 'Mês' },
    { chave: 'consumo', titulo: `Consumo (${UNIDADE[tipo]})`, numero: true },
    { chave: 'superPfx', titulo: 'Pfx Super' },
    { chave: 'superNome', titulo: 'Nome Super' },
    { chave: 'dirPfx', titulo: 'Pfx Diretoria' },
    { chave: 'dirNome', titulo: 'Nome Diretoria' },
    { chave: 'atualizadoEm', titulo: 'Dt Atualiz.' },
    { chave: 'responsavel', titulo: 'Responsável' },
  ];

  const ordenadas = useMemo(() => {
    const valor = (l: LinhaConsumo): string | number => (ordem.chave === 'consumo' ? l.valores[tipo] : l[ordem.chave]);
    const dir = ordem.asc ? 1 : -1;
    return [...linhas].sort((a, b) => {
      const va = valor(a), vb = valor(b);
      const c = typeof va === 'number' && typeof vb === 'number' ? va - vb : collator.compare(String(va), String(vb));
      // Desempate estável: prefixo e período.
      return c * dir || collator.compare(a.prefixo, b.prefixo) || b.ano - a.ano || b.mes - a.mes;
    });
  }, [linhas, ordem, tipo]);

  // Volta para a 1ª página quando os dados, o tipo ou a ordenação mudam.
  useEffect(() => { setPagina(1); }, [linhas, tipo, ordem]);

  const totalPaginas = Math.max(1, Math.ceil(ordenadas.length / POR_PAGINA));
  const atual = Math.min(pagina, totalPaginas);
  const inicio = (atual - 1) * POR_PAGINA;
  const visiveis = ordenadas.slice(inicio, inicio + POR_PAGINA);

  const ordenar = (chave: Chave) => setOrdem((o) => (o.chave === chave ? { chave, asc: !o.asc } : { chave, asc: true }));

  if (!linhas.length) {
    return (
      <section className="rf-card rc-tabela rc-vazio" aria-live="polite">
        <FileSearch size={48} strokeWidth={1.5} aria-hidden="true" />
        <p>Nenhum dado disponível para os parâmetros aplicados.</p>
      </section>
    );
  }

  return (
    <section className="rf-card rc-tabela">
      <div className="rf-table-wrap rc-tabela__scroll">
        <table className="rf-table rc-table">
          <caption className="rf-sr">Consumo por agência e mês, em {UNIDADE[tipo]}</caption>
          <thead>
            <tr>
              {colunas.map((c) => {
                const ativa = ordem.chave === c.chave;
                const Icone = !ativa ? ArrowUpDown : ordem.asc ? ArrowUp : ArrowDown;
                return (
                  <th key={c.chave} scope="col" aria-sort={ativa ? (ordem.asc ? 'ascending' : 'descending') : 'none'} className={c.numero ? 'is-num' : undefined}>
                    <button type="button" className={`rc-sort${ativa ? ' is-active' : ''}`} onClick={() => ordenar(c.chave)}>
                      {c.titulo}
                      <Icone size={14} aria-hidden="true" />
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visiveis.map((l) => (
              <tr key={`${l.prefixo}-${l.ano}-${l.mes}`}>
                <th scope="row">{l.prefixo}</th>
                <td>{l.nome}</td>
                <td className="is-num">{l.ano}</td>
                <td>{MESES[l.mes - 1]}</td>
                <td className="is-num"><strong>{formatarConsumo(tipo, l.valores[tipo])}</strong></td>
                <td>{l.superPfx}</td>
                <td>{l.superNome}</td>
                <td>{l.dirPfx}</td>
                <td>{l.dirNome}</td>
                <td>{data(l.atualizadoEm)}</td>
                <td>{l.responsavel}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <footer className="rc-paginacao">
        <span>Mostrando {inicio + 1}–{inicio + visiveis.length} de {ordenadas.length}</span>
        <div className="rc-paginacao__nav">
          <button type="button" onClick={() => setPagina(atual - 1)} disabled={atual <= 1} aria-label="Página anterior"><ChevronLeft size={16} aria-hidden="true" /></button>
          <span aria-live="polite">Página {atual} de {totalPaginas}</span>
          <button type="button" onClick={() => setPagina(atual + 1)} disabled={atual >= totalPaginas} aria-label="Próxima página"><ChevronRight size={16} aria-hidden="true" /></button>
        </div>
      </footer>
    </section>
  );
}
