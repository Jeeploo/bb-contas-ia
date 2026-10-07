import type { Calculo, EstrategiaCalculo, PerfilProcessamento, DadoExtraido } from '../types';
import { date, money, Table } from './ui';
export const estrategias: Record<EstrategiaCalculo, { nome: string; descricao: string }> = {
    VALOR_INTEGRAL: { nome: 'Valor integral', descricao: 'Utiliza o valor validado da conta.' },
    COEFICIENTE: { nome: 'Cálculo por coeficiente', descricao: 'Divide o valor base pelo coeficiente configurado para o Prefixo.' },
    COMPOSICAO_DETALHADA: { nome: 'Composição detalhada', descricao: 'Calcula o resultado com os componentes configurados na regra.' },
};
export function perfisVigentes(perfis: PerfilProcessamento[], idPrefixo: number, competencia: string) {
    const referencia = /^\d{4}-\d{2}$/.test(competencia) ? competencia + '-01' : '';
    return perfis.filter(p => p.id_prefixo === idPrefixo && p.situacao === 'ativo' && referencia && p.data_inicio_vigencia <= referencia && (!p.data_fim_vigencia || p.data_fim_vigencia >= referencia));
}
export function competenciaReferencia(dados: DadoExtraido[], fallback: string) {
    return dados.find(d => d.campo_identificado === 'competencia' && d.situacao_validacao === 'validada')?.valor_validado ?? fallback;
}
export function Vigencia({ inicio, fim }: { inicio: string; fim: string | null }) {
    return <>{date(inicio)} até {fim ? date(fim) : 'sem data final'}</>;
}
export function MemoriaCalculoView({ calculo }: { calculo: Calculo }) {
    const m = calculo.memoria_calculo;
    if (!m) return <p>Este cálculo histórico não possui memória retornada pela API.</p>;
    return <article className="calculation-memory"><h3>Cálculo #{calculo.id_calculo} · {date(calculo.data_calculo)}</h3>
        <div className="summary"><article><span>Estratégia</span><strong>{estrategias[m.estrategia]?.nome ?? m.estrategia}</strong></article><article><span>Valor base validado</span><strong>{money(m.valor_base)}</strong></article>{m.parametros.coeficiente !== undefined && <article><span>Coeficiente</span><strong>{Number(m.parametros.coeficiente).toLocaleString('pt-BR', { maximumFractionDigits: 10 })}</strong></article>}<article><span>Resultado final</span><strong>{money(m.resultado)}</strong></article></div>
        {m.estrategia === 'VALOR_INTEGRAL' && <p>Cálculo: {money(m.valor_base)} = {money(m.resultado)}</p>}
        {m.estrategia === 'COEFICIENTE' && m.parametros.coeficiente !== undefined && <p>Cálculo: {money(m.valor_base)} ÷ {Number(m.parametros.coeficiente).toLocaleString('pt-BR', { maximumFractionDigits: 10 })} = {money(m.resultado)}</p>}
        {m.componentes_considerados.length > 0 && <><h3>Componentes considerados e descontos</h3><Table rows={m.componentes_considerados} rowKey={c => c.id} columns={[{ title: 'Componente', render: c => c.tipo }, { title: 'Operação', render: c => c.operacao === 'DESCONTO' ? 'Desconto' : 'Soma' }, { title: 'Valor validado', render: c => `${c.operacao === 'DESCONTO' ? '−' : '+'} ${money(c.valor)}` }]}/></>}
        <details><summary>Componentes ignorados ({m.componentes_ignorados.length}) e rastreabilidade</summary><Table rows={m.componentes_ignorados} rowKey={c => c.id} columns={[{ title: 'Componente', render: c => c.tipo }, { title: 'Valor validado', render: c => c.valor === null ? 'Não validado' : money(c.valor) }]}/><p>Prefixo cadastrado · Perfil #{m.id_perfil} · Regra #{m.id_regra}, versão {m.versao_regra} · Extração #{m.id_extracao} · Competência {m.competencia}</p></details>
    </article>;
}
