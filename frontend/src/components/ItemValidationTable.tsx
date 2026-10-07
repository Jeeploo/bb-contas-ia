import { useState } from 'react';
import { api } from '../api';
import { errorMessage } from '../api/client';
import type { ItemExtraido } from '../types';
import { Badge, Notice, Table, confidence, money } from './ui';
function ItemActions({ item, reload }: { item: ItemExtraido; reload: () => void }) {
    const [value, setValue] = useState(String(item.valor_validado ?? item.valor));
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    async function save(correct: boolean) {
        setBusy(true); setError(''); setSuccess('');
        try { const saved = await api.validarItem(item.id_item_extraido, correct ? value : undefined); setValue(String(saved.valor_validado)); setSuccess('Validação salva.'); reload(); }
        catch (e) { setError(errorMessage(e)); }
        finally { setBusy(false); }
    }
    return <div className="validation-actions"><input type="number" min="0" step="0.01" aria-label={`Valor validado de ${item.descricao_original}, item ${item.id_item_extraido}`} value={value} disabled={busy} onChange={e => setValue(e.target.value)}/><div className="button-row"><button disabled={busy} onClick={() => void save(false)}>Confirmar original</button><button className="primary" disabled={busy || !value.trim() || Number(value) < 0} onClick={() => void save(true)}>Enviar correção</button></div>{error && <Notice kind="error">{error}</Notice>}{success && <Notice>{success}</Notice>}</div>;
}
export function ItemValidationTable({ itens, reload }: { itens: ItemExtraido[]; reload: () => void }) {
    return <Table rows={itens} rowKey={i => i.id_item_extraido} columns={[
        { title: 'Descrição original → Tipo normalizado', render: i => <>{i.descricao_original}<strong className="normalized">→ {i.tipo_normalizado}</strong><details><summary>Detalhes do componente</summary><dl><dt>Categoria</dt><dd>{i.categoria}</dd><dt>Quantidade / unidade</dt><dd>{i.quantidade ?? '—'} {i.unidade ?? ''}</dd><dt>Valor unitário</dt><dd>{i.valor_unitario === null ? '—' : money(i.valor_unitario)}</dd><dt>Base de cálculo</dt><dd>{i.base_calculo === null ? '—' : money(i.base_calculo)}</dd><dt>Alíquota</dt><dd>{i.aliquota ?? '—'}</dd></dl></details></> },
        { title: 'Valor extraído', render: i => money(i.valor) },
        { title: 'Confiança / situação', render: i => <>{confidence(i.nivel_confianca)}<small><Badge value={i.situacao_validacao}/></small>{i.nivel_confianca !== null && Number(i.nivel_confianca) < 80 && <Badge value="baixa confiança"/>}</> },
        { title: 'Valor validado', render: i => i.valor_validado === null ? '—' : money(i.valor_validado) },
        { title: 'Validação humana', render: i => <ItemActions key={i.id_item_extraido} item={i} reload={reload}/> },
    ]}/>;
}
