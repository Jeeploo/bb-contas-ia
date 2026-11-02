import { listAll, request } from './client';
import type { ItemRegra, PerfilProcessamento, ItemExtraido, RespostaCalculoContextual, Localidade, RegraCalculo, ContaConsumo, Documento, ExtracaoInteligente, DadoExtraido, Calculo, OrdemPagamento, ItemPagamento, Aprovacao, Usuario, Alcada, Prefixo, Concessionaria, SistemaPagamento, ProcessamentoDocumento } from '../types';
export const api = {
    revalidarExtracao: (id: number) => request<ExtracaoInteligente>(`/extracoes_inteligentes/${id}/revalidar`, { method: 'POST' }),
    enviarValidacao: (id: number) => request<ExtracaoInteligente>(`/extracoes_inteligentes/${id}/enviar-validacao`, { method: 'POST' }),
    prefixosUsuario: (id: number) => request<{ vinculos: { id_prefixo: number; ativo: boolean }[] }>(`/usuarios/${id}/prefixos`),
    uploadInicial: (file: File) => {
        const body = new FormData(); body.append('file', file);
        return request<Documento>('/documentos/upload', { method: 'POST', body });
    },
    processarInteligente: (id: number) => request<ProcessamentoDocumento>(`/documentos/${id}/processar-inteligente`, { method: 'POST' }),
    perfis: () => listAll<PerfilProcessamento>('perfis_processamento'),
    itensExtraidos: () => listAll<ItemExtraido>('itens_extraidos'),
    localidades: () => listAll<Localidade>('localidades'),
    itensRegra: () => listAll<ItemRegra>('itens_regra'),
    regras: () => listAll<RegraCalculo>('regras_calculo'),
    validarItem: (id: number, valor?: string) => request<ItemExtraido>(`/itens_extraidos/${id}/validacao`, { method: 'PATCH', body: JSON.stringify(valor === undefined ? {} : { valor_validado: valor }) }),
    calcular: (id: number) => request<RespostaCalculoContextual>(`/contas_consumo/${id}/calcular`, { method: 'POST' }),
    contas: () => listAll<ContaConsumo>('contas_consumo'), conta: (id: number) => request<ContaConsumo>(`/contas_consumo/${id}`),
    documentos: () => listAll<Documento>('documentos'), extracoes: () => listAll<ExtracaoInteligente>('extracoes_inteligentes'), dados: () => listAll<DadoExtraido>('dados_extraidos'),
    calculos: () => listAll<Calculo>('calculos'), ordens: () => listAll<OrdemPagamento>('ordens_pagamento'), ordem: (id: number) => request<OrdemPagamento>(`/ordens_pagamento/${id}`), itens: () => listAll<ItemPagamento>('itens_pagamento'),
    aprovacoes: () => listAll<Aprovacao>('aprovacoes'), usuarios: () => listAll<Usuario>('usuarios'), alcadas: () => listAll<Alcada>('alcadas'), prefixos: () => listAll<Prefixo>('prefixos'), concessionarias: () => listAll<Concessionaria>('concessionarias'), sistemas: () => listAll<SistemaPagamento>('sistemas_pagamento'),
    upload: (id: number, file: File) => { const body = new FormData(); body.append('file', file); return request<Documento>(`/contas_consumo/${id}/documentos/upload`, { method: 'POST', body }); },
    processar: (id: number) => request<ProcessamentoDocumento>(`/documentos/${id}/processar`, { method: 'POST' }),
    validar: (id: number, valor?: string) => request<DadoExtraido>(`/dados_extraidos/${id}/validacao`, { method: 'PATCH', body: JSON.stringify(valor === undefined ? {} : { valor_validado: valor }) }),
    decidir: (id_ordem: number, decisao: 'aprovado' | 'rejeitado', observacao: string) => request<Aprovacao>('/aprovacoes', { method: 'POST', body: JSON.stringify({ id_ordem, decisao, observacao: observacao || null, data_hora: new Date().toISOString() }) }),
};
