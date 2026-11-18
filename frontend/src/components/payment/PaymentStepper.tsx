import type { CSSProperties, KeyboardEvent } from "react";
/** step = etapa exibida; reached = etapa mais avançada já alcançada (clicáveis: 1..reached). */
export function PaymentStepper({ step, reached = step, onSelect }: { step: number; reached?: number; onSelect?: (step: number) => void }) {
  const furthest = Math.max(step, reached);
  return (
    <ol className="stepper" aria-label="Etapas do pagamento" style={{ "--stepper-progress": Math.min(Math.max(furthest - 1, 0), 3) / 3 } as CSSProperties}>
      {[
        "Upload da fatura",
        "Resumo da fatura",
        "Validação e cálculo",
        "Processamento concluído",
      ].map((label, i) => {
        const n = i + 1;
        const clickable = !!onSelect && n <= furthest;
        const select = () => { if (clickable && n !== step) onSelect?.(n); };
        return (
          <li
            key={label}
            className={[n === step ? "active" : n <= furthest ? "complete" : "", clickable ? "clickable" : ""].filter(Boolean).join(" ")}
            aria-current={n === step ? "step" : undefined}
            role={clickable ? "button" : undefined}
            tabIndex={clickable ? 0 : undefined}
            aria-label={clickable ? `Ir para a etapa ${n}: ${label}` : undefined}
            onClick={select}
            onKeyDown={(e: KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(); } }}
          >
            <span>{n !== step && n <= furthest ? "✓" : n}</span>
            {label}
          </li>
        );
      })}
    </ol>
  );
}
