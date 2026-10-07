import { useState } from 'react';
import { api } from '../api';
import { errorMessage } from '../api/client';
import type { DadoExtraido } from '../types';
import { Badge, Notice, Table, confidence } from './ui';
function ValidationRow({ dado, reload }: {
    dado: DadoExtraido;
    reload: () => void;
}) {
    const [value, setValue] = useState(dado.valor_validado ?? dado.valor_extraido ?? '');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    async function send(correct: boolean) { setBusy(true); setError(''); setSuccess(''); try {
        const saved = await api.validar(dado.id_dado_extraido, correct ? value : undefined);
        setValue(saved.valor_validado ?? '');
        setSuccess('Validação salva.');
        reload();
    }
    catch (e) {
        setError(errorMessage(e));
    }
    finally {
        setBusy(false);
    } }
    return <div className="validation-actions"><input aria-label={`Valor validado de ${dado.campo_identificado}, registro ${dado.id_dado_extraido}`} value={value} onChange={e => setValue(e.target.value)} disabled={busy}/><div className="button-row"><button disabled={busy || dado.valor_extraido === null} onClick={() => void send(false)}>Confirmar original</button><button className="primary" disabled={busy || !value.trim()} onClick={() => void send(true)}>{busy ? 'Enviando…' : 'Enviar correção'}</button></div>{error && <Notice kind="error">{error}</Notice>}{success && <Notice>{success}</Notice>}</div>;
}
export function ValidationTable({ dados, reload }: {
    dados: DadoExtraido[];
    reload: () => void;
}) { return <Table rows={dados} rowKey={d => d.id_dado_extraido} columns={[{ title: 'Campo / extração', render: d => <>{({ competencia: 'Competência', data_vencimento: 'Vencimento', valor_original: 'Valor total', consumo: 'Consumo', codigo_barras: 'Código de barras' } as Record<string, string>)[d.campo_identificado] ?? d.campo_identificado}<small>Extração #{d.id_extracao}</small></> }, { title: 'Valor extraído', render: d => d.valor_extraido ?? '—' }, { title: 'Confiança', render: d => <>{confidence(d.nivel_confianca)}{d.nivel_confianca !== null && Number(d.nivel_confianca) < 80 && <small><Badge value="baixa confiança"/></small>}</> }, { title: 'Situação', render: d => <Badge value={d.situacao_validacao}/> }, { title: 'Valor validado', render: d => d.valor_validado ?? '—' }, { title: 'Validação humana', render: d => <ValidationRow key={d.id_dado_extraido} dado={d} reload={reload}/> }]}/>; }
