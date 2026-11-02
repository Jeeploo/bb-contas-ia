import { useEffect, useState } from 'react';
import { advanceProcessingProgress, processingActivities, processingActivityState, type ProcessingPhase } from '../../utils/processingProgress';
import { Alert } from './DocumentaryAlerts';

export function ProcessingState({ phase, received = false, error, onComplete, onRetry, onBack }: {
  phase: ProcessingPhase; received?: boolean; error: string; onComplete: () => void; onRetry: () => void; onBack: () => void;
}) {
  const [progress, setProgress] = useState(0);
  const percentage = Math.floor(progress);
  const finished = phase === 'complete' && percentage === 100;
  useEffect(() => {
    if (phase === 'error') return;
    const timer = window.setInterval(() => setProgress(value => advanceProcessingProgress(value, phase)), 150);
    return () => window.clearInterval(timer);
  }, [phase]);
  useEffect(() => {
    if (!finished) return;
    // Permite perceber a conclusão antes de trocar de tela; cancelado ao desmontar.
    const timer = window.setTimeout(onComplete, 700);
    return () => window.clearTimeout(timer);
  }, [finished, onComplete]);
  return <section className={`card processing${phase === 'error' ? ' processing-error' : ''}`} data-phase={phase} aria-labelledby="processing-title" aria-busy={!finished && phase !== 'error'}>
    <div className="processing-progress" role="progressbar" aria-label="Progresso do processamento da fatura"
      aria-valuemin={0} aria-valuemax={100} aria-valuenow={percentage}
      aria-valuetext={`${percentage}%${phase === 'error' ? ' — processamento interrompido' : finished ? ' — leitura concluída' : ' — progresso estimado'}`}>
      <svg className="processing-ring" viewBox="0 0 120 120" aria-hidden="true">
        <circle className="processing-ring-track" cx="60" cy="60" r="52" />
        <circle className="processing-ring-value" cx="60" cy="60" r="52" pathLength="100" strokeDasharray="100" strokeDashoffset={100 - progress} />
      </svg>
      <div className="processing-percentage"><strong>{percentage}%</strong><span>{phase === 'error' ? 'Processamento interrompido' : finished ? 'Leitura concluída' : 'Processando sua fatura'}</span></div>
    </div>
    <h2 id="processing-title">{phase === 'error' ? 'Não foi possível concluir a leitura' : finished ? 'Resumo pronto para revisão' : 'Lendo e interpretando sua fatura...'}</h2>
    <p>{phase === 'error' ? 'Você pode tentar novamente ou escolher outro arquivo.' : finished ? 'As informações foram organizadas. Confira os dados no resumo.' : 'Aguarde enquanto as informações da fatura são organizadas.'}</p>
    <p className="processing-estimate">{!finished && phase !== 'error' ? 'Progresso estimado por fases. A leitura será confirmada ao final.' : '\u00a0'}</p>
    <ul aria-label="Atividades do processamento">
      {processingActivities.map((activity, index) => {
        const state = processingActivityState(index, received ? Math.max(18, progress) : progress, phase);
        return <li key={activity} className={`processing-activity ${state}`} aria-current={state === 'active' ? 'step' : undefined}>
          <span className="processing-activity-icon" aria-hidden="true">{state === 'complete' ? '✓' : state === 'error' ? '!' : state === 'active' ? '•' : ''}</span>
          <span>{activity}<span className="sr-only"> — {state === 'complete' ? 'concluída' : state === 'active' ? 'em andamento' : state === 'error' ? 'interrompida' : 'pendente'}</span></span>
        </li>;
      })}
    </ul>
    <div role="status" className="sr-only">{phase === 'error' ? 'Processamento interrompido.' : finished ? 'Leitura concluída. Abrindo resumo.' : 'Processamento em andamento.'}</div>
    {phase === 'error' && <><Alert variant="error">{error}</Alert><div className="actions">
      <button onClick={onBack}>Escolher outro arquivo</button><button className="primary" onClick={onRetry}>Tentar novamente</button>
    </div></>}
  </section>;
}
