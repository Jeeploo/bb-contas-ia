import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import type { ExtracaoInteligente } from "../../types";
import { documentaryMessages } from "./InvoiceSummary";

export function canSubmitReview(extracao: ExtracaoInteligente) {
  return extracao.permite_envio_validacao === true;
}
export function Alert({ variant, children }: { variant: "info" | "warning" | "review" | "error"; children: ReactNode }) {
  return <div className={`documentary-alert documentary-alert-${variant}`} role={variant === "error" ? "alert" : "status"}><AlertTriangle size={18} aria-hidden="true" /><div>{children}</div></div>;
}
export function DocumentaryAlerts({ extracao, concessionaria, confirmado = false }: { extracao: ExtracaoInteligente; concessionaria?: string; confirmado?: boolean }) {
  const pendencias = extracao.pendencias ?? [];
  if (!pendencias.length) return <Alert variant={extracao.resultado_validacao_documental === "VALIDO" ? "info" : "review"}>{extracao.motivo_validacao_documental ?? documentaryMessages[extracao.resultado_validacao_documental ?? "EVIDENCIA_INSUFICIENTE"]}</Alert>;
  return <section aria-label="Pendências documentais"><h3>Pendências e alertas</h3>{pendencias.map((p, i) => {
    const blocking = p.bloqueia_envio_validacao || p.bloqueia_calculo;
    return <Alert variant={blocking ? "error" : "warning"} key={`${p.tipo}-${p.campo ?? i}`}>
      <strong>{blocking ? 'Erro bloqueante' : 'Pendência cadastral'}</strong><p>{p.mensagem}</p>
      {p.tipo === "CORRESPONDENCIA_CONCESSIONARIA" && <p>{concessionaria}</p>}
      {!blocking && <><p>A informação foi preservada e poderá ser revisada posteriormente.</p><p>Pendência que não impede continuar.</p></>}
      {confirmado && !blocking && <p>Dados documentais confirmados.</p>}
    </Alert>;
  })}</section>;
}
