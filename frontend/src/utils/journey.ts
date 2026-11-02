import type { ExtracaoInteligente, Calculo } from '../types';
export function journeyStep(extracao?: ExtracaoInteligente, calculo?: Calculo) {
  if (!extracao) return 1;
  if (extracao.situacao_validacao === 'revisao_cadastral_pendente' || extracao.bloqueia_calculo && extracao.situacao_validacao === 'validada') return 3;
  if (calculo?.id_calculo && !extracao.bloqueia_calculo) return 4;
  if (extracao.situacao_validacao === 'validada' || extracao.historico_validacao_documental?.some(h => h.evento === 'ENVIADO_PARA_VALIDACAO')) return 3;
  return 2;
}
