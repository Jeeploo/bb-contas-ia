import { Link } from 'react-router-dom';
import { api } from '../api';
import { Badge, PageTitle, ResourceState, Table, confidence, useResource } from '../components/ui';
import { competenciaReferencia, perfisVigentes } from '../components/CalculoContexto';
import { ValidationTable } from '../components/ValidationTable';
const loadDocs = async () => {
    const [contas, documentos, extracoes, dados, itens, perfis, prefixos, regras, itensRegra] = await Promise.all([api.contas(), api.documentos(), api.extracoes(), api.dados(), api.itensExtraidos(), api.perfis(), api.prefixos(), api.regras(), api.itensRegra()]);
    return contas.map(conta => {
        const docs = documentos.filter(d => d.id_conta === conta.id_conta);
        const ext = extracoes.filter(e => docs.some(d => d.id_documento === e.id_documento)).sort((a, b) => b.data_processamento.localeCompare(a.data_processamento) || b.id_extracao - a.id_extracao)[0];
        const campos = dados.filter(d => d.id_extracao === ext?.id_extracao);
        const componentes = itens.filter(i => i.id_extracao === ext?.id_extracao);
        const perfil = perfisVigentes(perfis, conta.id_prefixo, competenciaReferencia(campos, conta.competencia));
        const referencia = competenciaReferencia(campos, conta.competencia) + '-01';
        const selected = perfil.length === 1 ? perfil[0] : undefined;
        const regra = regras.find(r => r.id_regra === selected?.id_regra);
        const configuracao = selected && regra?.situacao === 'ativa' && regra.data_inicio_vigencia <= referencia && (!regra.data_fim_vigencia || regra.data_fim_vigencia >= referencia) && selected.tipo_servico === conta.categoria && (!selected.id_concessionaria || selected.id_concessionaria === conta.id_concessionaria) && (selected.estrategia !== 'COEFICIENTE' || (Number.isFinite(Number(selected.parametros.coeficiente)) && Number(selected.parametros.coeficiente) > 0));
        const camposValidados = ['competencia', 'valor_original'].every(nome => campos.some(c => c.campo_identificado === nome && c.situacao_validacao === 'validada' && c.valor_validado));
        const componentesRegra = itensRegra.filter(i => i.id_regra === selected?.id_regra);
        const itensValidados = selected?.estrategia !== 'COMPOSICAO_DETALHADA' || (componentesRegra.length > 0 && componentesRegra.every(regraItem => {
            const encontrados = componentes.filter(i => i.tipo_normalizado === regraItem.nome_item.toUpperCase());
            return (!regraItem.obrigatorio || encontrados.length > 0) && encontrados.every(i => i.situacao_validacao === 'validada' && i.valor_validado !== null);
        }));
        const etapa = !docs.length ? 'Aguardando documento' : !ext ? 'Aguardando leitura' : !camposValidados || !itensValidados ? 'Aguardando validação' : !configuracao ? 'Verificar perfil / regra' : 'Pronta para cálculo';
        return { conta, docs, ext, etapa, prefixo: prefixos.find(p => p.id_prefixo === conta.id_prefixo) };
    });
};
export function Processamento() {
    const r = useResource(loadDocs);
    return <><PageTitle title="Processamento" subtitle="Visão operacional por conta, do documento até o cálculo contextual" action={<button onClick={r.reload}>Atualizar</button>}/><ResourceState {...r} retry={r.reload}>{r.data && <><div className="metrics">{[
        ['Contas aguardando documento', r.data.filter(c => !c.docs.length).length],
        ['Contas processadas', r.data.filter(c => c.ext).length],
        ['Contas aguardando validação', r.data.filter(c => c.etapa === 'Aguardando validação').length],
        ['Contas prontas para cálculo', r.data.filter(c => c.etapa === 'Pronta para cálculo').length],
    ].map(([label, count]) => <article className="metric" key={label}><span>{label}</span><strong>{count}</strong></article>)}</div><p>Prontidão estimada pela última extração, validações e perfil vigente. O backend verifica componentes obrigatórios, regra, vigência e coeficiente ao calcular.</p><Table rows={r.data} rowKey={c => c.conta.id_conta} columns={[
        { title: 'Conta / Prefixo', render: c => <><Link to={`/contas/${c.conta.id_conta}`}>#{c.conta.id_conta} · Abrir conta</Link><small>{c.prefixo?.codigo_prefixo ?? 'Prefixo não disponível'}</small></> },
        { title: 'Etapa', render: c => <Badge value={c.etapa}/> },
        { title: 'Documento / leitura', render: c => c.ext ? `Documento #${c.ext.id_documento} processado` : `${c.docs.length} documento(s)` },
        { title: 'Estratégia de leitura', render: c => c.ext?.estrategia ?? 'Não informada pela API' },
        { title: 'Confiança geral', render: c => confidence(c.ext?.nivel_confianca ?? null) },
    ]}/></>}</ResourceState></>;
}
export function Validacoes() { const r = useResource(api.dados); return <><PageTitle title="Validações" subtitle="Revise os campos extraídos e preserve o registro original" action={<button onClick={r.reload}>Atualizar</button>}/><ResourceState {...r} retry={r.reload}>{r.data && <ValidationTable dados={r.data} reload={r.reload}/>}</ResourceState></>; }
