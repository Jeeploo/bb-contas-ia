export function PaymentStepper({ step }: { step: number }) {
  return (
    <ol className="stepper" aria-label="Etapas do pagamento">
      {[
        "Upload da fatura",
        "Resumo da fatura",
        "Validação e cálculo",
        "Processamento concluído",
      ].map((label, i) => (
        <li
          key={label}
          className={i + 1 === step ? "active" : i + 1 < step ? "complete" : ""}
          aria-current={i + 1 === step ? "step" : undefined}
        >
          <span>{i + 1 < step ? "✓" : i + 1}</span>
          {label}
        </li>
      ))}
    </ol>
  );
}
