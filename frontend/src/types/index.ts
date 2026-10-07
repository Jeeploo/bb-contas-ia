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
    memoria_calculo: MemoriaCalculo | null;
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
    id_localidade: number;
    situacao: string;
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
    itens_encontrados: ItemExtraido[];
    confianca_geral: Decimal | null;
    situacao: string;
    estrategia?: 'text' | 'ocr';
}

export type EstrategiaCalculo = 'VALOR_INTEGRAL' | 'COEFICIENTE' | 'COMPOSICAO_DETALHADA';
export interface PerfilProcessamento {
    id_perfil: number;
    id_prefixo: number;
    tipo_servico: string;
    estrategia: EstrategiaCalculo;
    id_regra: number;
    id_concessionaria: number | null;
    situacao: string;
    data_inicio_vigencia: string;
    data_fim_vigencia: string | null;
    parametros: Record<string, unknown> & { coeficiente?: Decimal };
}
export interface ItemExtraido {
    id_item_extraido: number;
    id_extracao: number;
    categoria: string;
    descricao_original: string;
    tipo_normalizado: string;
    quantidade: Decimal | null;
    unidade: string | null;
    valor_unitario: Decimal | null;
    valor: Decimal;
    base_calculo: Decimal | null;
    aliquota: Decimal | null;
    nivel_confianca: Decimal | null;
    valor_validado: Decimal | null;
    situacao_validacao: string;
}
export interface MemoriaCalculo {
    estrategia: EstrategiaCalculo;
    valor_base: Decimal;
    parametros: Record<string, unknown> & { coeficiente?: Decimal };
    componentes_considerados: { id: number; tipo: string; valor: Decimal; operacao: string }[];
    componentes_ignorados: { id: number; tipo: string; valor: Decimal | null }[];
    resultado: Decimal;
    resultado_sem_arredondamento: Decimal;
    id_perfil: number;
    id_regra: number;
    versao_regra: string;
    id_extracao: number;
    competencia: string;
}
export type RespostaCalculoContextual = Calculo & { memoria_calculo: MemoriaCalculo };
export interface Localidade { id_localidade: number; municipio: string; estado: string }
export interface RegraCalculo { id_regra: number; nome_regra: string; versao: string; situacao: string; data_inicio_vigencia: string; data_fim_vigencia: string | null }

export interface ItemRegra { id_item_regra: number; id_regra: number; nome_item: string; tipo_item: string; obrigatorio: boolean; ordem_aplicacao: number }
