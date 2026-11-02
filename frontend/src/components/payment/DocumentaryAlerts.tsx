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
  return <section aria-label="Pendências documentais"><h3>Pendência encontrada</h3>{pendencias.map((p, i) => <Alert variant="review" key={`${p.tipo}-${p.campo ?? i}`}>
    <strong>{p.mensagem}</strong>
    {p.tipo === "CORRESPONDENCIA_CONCESSIONARIA" && <><p>{concessionaria}</p><p>{(confirmado || extracao.situacao_validacao === "revisao_cadastral_pendente") ? "Os dados do documento foram confirmados, mas a concessionária ainda precisa ser associada ao cadastro." : "Confirme os dados do documento. A concessionária ainda precisa ser associada ao cadastro."}</p><p>A fatura pode ser enviada para revisão cadastral.</p></>}
  </Alert>)}</section>;
}
