export type Decimal = string | number;
export interface ContaConsumo {
    id_conta: number;
    numero_conta: string | null;
    competencia: string;
    data_emissao: string | null;
    data_vencimento: string;
    valor_original: Decimal;
    codigo_barras: string | null;
    consumo: Decimal | null;
    unidade_consumo: string | null;
    categoria: string;
    situacao: string;
    id_prefixo: number;
    id_concessionaria: number;
}
export interface Documento {
    id_documento: number;
    tipo_documento: string;
    formato: string;
    data_recebimento: string;
    origem: string;
    caminho_arquivo: string;
    id_conta: number;
}
export interface ExtracaoInteligente {
    id_extracao: number;
    data_processamento: string;
    nivel_confianca: Decimal | null;
    situacao_validacao: string;
    id_documento: number;
    estrategia?: 'text' | 'ocr';
}
export interface DadoExtraido {
    id_dado_extraido: number;
    campo_identificado: string;
    valor_extraido: string | null;
    nivel_confianca: Decimal | null;
    situacao_validacao: string;
    valor_validado: string | null;
    id_extracao: number;
}
export interface Calculo {
    id_calculo: number;
    data_calculo: string;
    valor_inicial: Decimal;
    valor_calculado: Decimal;
    situacao: string;
    id_conta: number;
    id_regra: number;
}
export interface OrdemPagamento {
    id_ordem: number;
    data_criacao: string;
    data_prevista_pagamento: string;
    valor_total: Decimal;
    situacao: string;
    id_calculo: number;
    id_sistema: number;
    id_usuario_criador: number;
}
export interface ItemPagamento {
    id_item_pagamento: number;
    codigo_evento: string;
    descricao_evento: string | null;
    codigo_subitem: string | null;
    descricao_subitem: string | null;
    valor: Decimal;
    id_ordem: number;
}
export interface Aprovacao {
    id_aprovacao: number;
    data_hora: string;
    decisao: string;
    observacao: string | null;
    id_ordem: number;
    id_usuario: number;
}
export interface Usuario {
    id_usuario: number;
    matricula: string;
    nome: string;
    funcao: string;
    situacao: string;
    id_alcada: number | null;
    id_prefixo: number | null;
}
export interface Alcada {
    id_alcada: number;
    nome_nivel: string;
    limite_financeiro: Decimal;
    data_inicio_vigencia: string;
    data_fim_vigencia: string | null;
}
export interface Prefixo {
    id_prefixo: number;
    codigo_prefixo: string;
    nome: string;
}
export interface Concessionaria {
    id_concessionaria: number;
    razao_social: string;
    nome_fantasia: string | null;
}
export interface SistemaPagamento {
    id_sistema: number;
    nome: string;
}
export interface ProcessamentoDocumento {
    documento: Documento;
    extracao: ExtracaoInteligente;
    campos_encontrados: DadoExtraido[];
    confianca_geral: Decimal | null;
    situacao: string;
    estrategia?: 'text' | 'ocr';
}
