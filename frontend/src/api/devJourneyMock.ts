// Mock da jornada "Pagamento de faturas" para o bypass de desenvolvimento.
// Usado apenas pelas funções de src/api/index.ts quando isDevBypass() é true.
// Estado em memória: recarregar a página recomeça a jornada.
import { mockDelay } from '../config/devBypass';
import type { DadoExtraido, Documento, ItemExtraido, JornadaPersistida, ProcessamentoDocumento, ResultadoCalculo } from '../types';

type Tipo = 'energia' | 'agua';
const FORMATOS = ['pdf', 'jpg', 'jpeg', 'png'];

let nextId = 1000;
let state: { documento: Documento; tipo: Tipo; processamento: ProcessamentoDocumento | null; calculo: ResultadoCalculo | null } | null = null;

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));
const snapshot = (): JornadaPersistida => state
  ? clone({ documento: state.documento, processamento: state.processamento, calculo: state.calculo })
  : { documento: null, processamento: null, calculo: null };

function requireDoc(id: number) {
  if (!state || state.documento.id_documento !== id) throw new Error('Modo DEV: documento não encontrado. Clique em "Nova fatura" e envie novamente.');
  return state;
}

const FIXTURES: Record<Tipo, { campos: [string, string][]; itens: [string, string, string][]; concessionaria: string }> = {
  energia: {
    concessionaria: 'Concessionária Demo Energia',
    campos: [
      ['tipo_documento', 'Energia elétrica'], ['valor_total', '1610.45'], ['data_vencimento', '15/11/2026'],
      ['competencia', '2026-10'], ['concessionaria', 'Concessionária Demo Energia'], ['unidade_consumidora', '7012345678'],
      ['consumo', '1250'], ['unidade_consumo', 'kWh'], ['codigo_barras', '83690000016 1 10450048100 5 00000000000 0 70123456782 3'],
      ['municipio', 'Recife'], ['uf', 'PE'],
    ],
    itens: [['TUSD', 'Uso do sistema de distribuição', '612.30'], ['TE', 'Energia consumida', '701.85'], ['ICMS', 'ICMS', '254.10'], ['ILUMINACAO_PUBLICA', 'Contribuição iluminação pública', '42.20']],
  },
  agua: {
    concessionaria: 'Concessionária Demo Saneamento',
    campos: [
      ['tipo_documento', 'Água e esgoto'], ['valor_total', '312.90'], ['data_vencimento', '20/11/2026'],
      ['competencia', '2026-10'], ['concessionaria', 'Concessionária Demo Saneamento'], ['unidade_consumidora', '0045871'],
      ['consumo', '38'], ['unidade_consumo', 'm³'], ['codigo_barras', '82650000003 1 12900481001 2 00000000000 0 00458710000 4'],
      ['municipio', 'Recife'], ['uf', 'PE'],
    ],
    itens: [['TARIFA_AGUA', 'Tarifa de água', '173.83'], ['TARIFA_ESGOTO', 'Tarifa de esgoto', '139.07']],
  },
};

function buildProcessamento(documento: Documento, tipo: Tipo): ProcessamentoDocumento {
  const id_extracao = documento.id_documento + 5000;
  const fx = FIXTURES[tipo];
  const campos: DadoExtraido[] = fx.campos.map(([campo, valor], i) => ({
    id_dado_extraido: id_extracao * 100 + i, campo_identificado: campo, valor_extraido: valor, valor_normalizado: valor,
    nivel_confianca: '0.94', situacao_validacao: 'pendente', valor_validado: null, id_extracao,
  }));
  const itens: ItemExtraido[] = fx.itens.map(([tipo_normalizado, descricao, valor], i) => ({
    id_item_extraido: id_extracao * 100 + 50 + i, id_extracao, categoria: tipo, descricao_original: descricao, tipo_normalizado,
    quantidade: null, unidade: null, valor_unitario: null, valor, base_calculo: null, aliquota: null,
    nivel_confianca: '0.91', valor_validado: null, situacao_validacao: 'pendente',
  }));
  return {
    documento,
    extracao: {
      id_extracao, id_documento: documento.id_documento, data_processamento: new Date().toISOString(),
      nivel_confianca: '0.93', situacao_validacao: 'pendente', estrategia: documento.formato === 'pdf' ? 'text' : 'ocr',
      pendencias: [], permite_envio_validacao: true, bloqueia_calculo: false,
      resultado_validacao_documental: 'aprovado', historico_validacao_documental: [],
      evidencias_validacao_documental: { nome_concessionaria: fx.concessionaria },
    },
    campos_encontrados: campos, itens_encontrados: itens, confianca_geral: '0.93', situacao: 'processado',
    estrategia: documento.formato === 'pdf' ? 'text' : 'ocr',
  };
}

export const devJourneyMock = {
  async retomarJornada(): Promise<JornadaPersistida> { return snapshot(); },

  async jornadaDocumento(id: number): Promise<JornadaPersistida> { requireDoc(id); return snapshot(); },

  async uploadInicial(file: File): Promise<Documento> {
    await mockDelay();
    const formato = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!FORMATOS.includes(formato)) throw new Error('Formato não suportado. Envie um arquivo PDF, JPG ou PNG.');
    const documento: Documento = {
      id_documento: ++nextId, tipo_documento: 'fatura', formato: formato === 'jpeg' ? 'jpg' : formato,
      data_recebimento: new Date().toISOString(), origem: 'upload', caminho_arquivo: file.name, id_conta: null,
    };
    // Nome do arquivo com "agua"/"água" gera fatura de água; o resto, energia.
    state = { documento, tipo: /[aá]gua|saneamento/i.test(file.name) ? 'agua' : 'energia', processamento: null, calculo: null };
    return clone(documento);
  },

  async processarInteligente(id: number): Promise<ProcessamentoDocumento> {
    await mockDelay();
    const s = requireDoc(id);
    s.processamento = buildProcessamento(s.documento, s.tipo);
    s.calculo = null;
    return clone(s.processamento);
  },

  async confirmarJornada(id: number, valores: Record<string, string>, enviar: boolean): Promise<JornadaPersistida> {
    await mockDelay();
    const s = requireDoc(id);
    const p = s.processamento;
    if (!p) throw new Error('Modo DEV: processe o documento antes de validar.');
    for (const [key, value] of Object.entries(valores)) {
      const n = Number(key.slice(1));
      const campo = p.campos_encontrados.find(c => c.id_dado_extraido === n);
      if (campo) campo.valor_validado = value;
      const item = p.itens_encontrados.find(i => i.id_item_extraido === n);
      if (item) item.valor_validado = value;
    }
    if (enviar) {
      p.campos_encontrados.forEach(c => { c.situacao_validacao = 'validada'; });
      p.itens_encontrados.forEach(i => { i.situacao_validacao = 'validada'; });
      p.extracao.situacao_validacao = 'validada';
      p.extracao.historico_validacao_documental = [...(p.extracao.historico_validacao_documental ?? []), { evento: 'ENVIADO_PARA_VALIDACAO', data: new Date().toISOString() }];
    }
    s.calculo = null;
    return snapshot();
  },

  async calcularDocumento(id: number): Promise<ResultadoCalculo> {
    await mockDelay();
    const s = requireDoc(id);
    const p = s.processamento;
    if (!p || p.extracao.situacao_validacao !== 'validada') throw new Error('Modo DEV: envie a fatura para validação antes de calcular.');
    const total = p.campos_encontrados.find(c => c.campo_identificado === 'valor_total');
    const valor = String(total?.valor_validado ?? total?.valor_extraido ?? '0');
    s.calculo = {
      data_calculo: new Date().toISOString(), valor_inicial: valor, valor_calculado: valor, situacao: 'validado',
      memoria_calculo: null, id_regra: null, id_conta: null, id_extracao: p.extracao.id_extracao, origem: 'documental_demo',
    };
    return clone(s.calculo);
  },

  async novaFatura(): Promise<void> { state = null; },
};
