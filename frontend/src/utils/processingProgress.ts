export type ProcessingPhase = 'uploading' | 'extracting' | 'validating' | 'complete' | 'error';

// Sem eventos granulares do backend, o avanço intermediário é uma estimativa.
// Cada fronteira HTTP limita o avanço; 100% exige leitura e revalidação concluídas.
export function advanceProcessingProgress(current: number, phase: ProcessingPhase): number {
  if (phase === 'error') return current;
  if (phase === 'complete') return Math.min(100, current + Math.max(1, Math.min(6, (100 - current) / 4)));
  const [floor, ceiling] = phase === 'uploading' ? [0, 16] : phase === 'extracting' ? [18, 78] : [80, 94];
  return Math.min(ceiling, Math.max(floor, current + Math.max(0.15, (ceiling - current) / 24)));
}

export const processingActivities = [
  'Documento recebido', 'Extraindo informações', 'Identificando tipo de fatura',
  'Lendo valores e datas', 'Validação cadastral', 'Preparando resumo',
];
const thresholds = [0, 18, 38, 58, 80, 95];
export function processingActivityState(index: number, progress: number, phase: ProcessingPhase) {
  if (phase === 'complete' && progress >= 100) return 'complete';
  const active = thresholds.reduce((last, threshold, i) => progress >= threshold ? i : last, 0);
  if (index < active) return 'complete';
  if (index === active) return phase === 'error' ? 'error' : 'active';
  return 'pending';
}
