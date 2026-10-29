export function PaymentStepper({ step }: { step: number }) {
  return (
    <ol className="stepper" aria-label="Etapas do pagamento">
      {[
        "Upload da fatura",
        "Resumo da fatura",
        "Validação",
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
export function ProcessingState({ received }: { received: boolean }) {
  return (
    <section className="card processing" role="status">
      <div className="loader" />
      <h2>Lendo e interpretando sua fatura...</h2>
      <p>Aguarde enquanto as informações da fatura são organizadas.</p>
      <ul aria-label="Atividades da leitura em andamento">
        {[
          "Documento recebido",
          "Extraindo informações",
          "Identificando tipo de fatura",
          "Lendo valores e datas",
          "Aplicando regras de cálculo",
        ].map((s, i) => (
          <li key={s}>
            {i === 0 && received ? "✓" : "○"} {s}
          </li>
        ))}
      </ul>
    </section>
  );
}
