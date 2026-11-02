import { apiBase } from "../../api/config";
import { FileText } from "lucide-react";
import { useEffect, useState } from "react";

import type { DadoExtraido, ItemExtraido, ResultadoCalculo as Calculo } from "../../types";
import { formatCompetenciaDisplay } from "../../utils/competencia";
import { money } from "../ui";
export const labels: Record<string, string> = {
  tipo_documento: "Tipo da fatura",
  valor_total: "Valor da fatura",
  municipio: "Município",
  uf: "UF",
  unidade_consumo: "Unidade de consumo",
  bandeira_tarifaria: "Bandeira tarifária",
  data_emissao: "Emissão",
  numero_documento: "Número do documento",
  endereco_unidade: "Endereço da unidade",
  leitura_anterior: "Leitura anterior",
  leitura_atual: "Leitura atual",
  periodo_leitura: "Período de leitura",
  demanda: "Demanda",
  categoria: "Tipo da fatura",
  tipo_servico: "Tipo da fatura",
  valor_original: "Valor da fatura",
  data_vencimento: "Data de vencimento",
  codigo_barras: "Código de barras",
  competencia: "Competência",
  prefixo: "Prefixo",
  agencia: "Agência",
  concessionaria: "Concessionária",
  unidade_consumidora: "Unidade consumidora",
  numero_conta: "Unidade consumidora",
  consumo: "Consumo",
};
export const itemLabels: Record<string, string> = {
  TUSD: "TUSD", TE: "TE", PIS: "PIS", COFINS: "COFINS", ICMS: "ICMS",
  BANDEIRA: "Bandeira tarifária", ILUMINACAO_PUBLICA: "Iluminação pública",
  TARIFA_AGUA: "Tarifa de água", TARIFA_ESGOTO: "Tarifa de esgoto",
  SERVICOS_ADICIONAIS: "Serviços adicionais", DESCONTO: "Descontos",
  MULTA: "Multas", JUROS: "Juros", OUTROS_ENCARGOS: "Outros encargos",
};
export const documentaryMessages: Record<string, string> = {
  VALIDO: "Dados compatíveis com a unidade selecionada.",
  DIVERGENCIA_PREFIXO: "Esta fatura não corresponde à unidade/prefixo selecionado.",
  REGIAO_NAO_SUPORTADA: "A fatura pertence a uma região ainda não suportada.",
  DOCUMENTO_NAO_SUPORTADO: "O arquivo enviado não foi identificado como conta de energia ou água.",
  EVIDENCIA_INSUFICIENTE: "Alguns dados precisam ser conferidos antes de continuar.",
};
export type SummaryField = { label: string; value: string };
export function InvoiceSummary({ fields }: { fields: SummaryField[] }) {
  return (
    <dl className="invoice-fields">
      {fields.map((f) => (
        <div key={f.label} className={f.label === "Código de barras" ? "barcode-field" : ""}>
          <dt>{f.label}</dt>
          <dd>{["Data de vencimento", "Emissão"].includes(f.label) && /^\d{4}-\d{2}-\d{2}$/.test(f.value) ? f.value.split("-").reverse().join("/") : f.label === "Competência" ? formatCompetenciaDisplay(f.value) : ["Unidade consumidora", "Código de barras"].includes(f.label) ? `***${f.value.slice(-4)}` : f.label === "Tipo da fatura" ? ({ CONTA_ENERGIA: "Energia", CONTA_AGUA: "Água", OUTRO: "Outro" }[f.value] ?? f.value) : f.value}</dd>
        </div>
      ))}
    </dl>
  );
}
export function DocumentPreview({ file, documentId, documentFormat }: { file?: File; documentId?: number; documentFormat?: string }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (!file) return;
    const value = URL.createObjectURL(file);
    setUrl(value);
    return () => URL.revokeObjectURL(value);
  }, [file]);
  const previewUrl = url || (documentId ? `${apiBase(import.meta.env.VITE_API_URL)}/documentos/${documentId}/arquivo` : "");
  const imageDocument = file?.type.startsWith("image/") || ["png", "jpg", "jpeg"].includes(documentFormat ?? "");
  return (
    <section className="card document-preview">
      <h3>Documento enviado</h3>
      {previewUrl && imageDocument ? <img className="preview-image" src={previewUrl} alt="Fatura enviada" /> : previewUrl ? <object className="preview-pdf" data={previewUrl + "#toolbar=0&navpanes=0&view=Fit"} type="application/pdf"><p><FileText aria-hidden="true" /> Prévia indisponível. Abra o documento original.</p></object> : <p><FileText aria-hidden="true" /> Prévia indisponível. Abra o documento original.</p>}
      <small className="preview-caption">Use “Abrir documento” para consultar a fatura original.</small>
      <strong>{file?.name ?? `Fatura #${documentId ?? ""}`}</strong>
      <p>{imageDocument ? "Imagem" : "PDF"} da fatura</p>
      {previewUrl && (
        <a className="button" href={previewUrl} target="_blank" rel="noreferrer">
          Abrir documento
        </a>
      )}
    </section>
  );
}
export function CalculationSummary({ calculo }: { calculo?: Calculo }) {
  return (
    <section className="calculation">
      <div>
        <span>
          Valor original
        </span>
        <strong>
          {calculo ? money(calculo.valor_inicial) : "Aguardando revisão"}
        </strong>
      </div>
      <div>
        <span>Valor calculado</span>
        <strong>
          {calculo ? money(calculo.valor_calculado) : "Aguardando revisão"}
        </strong>
      </div>
      {calculo && <p>Diferença: {calculo.memoria_calculo?.diferenca !== undefined ? money(calculo.memoria_calculo.diferenca) : "Não informada"}</p>}
      {calculo?.memoria_calculo?.nome_regra && <p>Regra aplicada: <strong>{calculo.memoria_calculo.nome_regra}</strong></p>}
      {calculo?.memoria_calculo?.operacao === 'DIVISAO' && <>
        <p>Coeficiente: {String(calculo.memoria_calculo.coeficiente).replace('.', ',')}</p>
        <p>Operação aplicada: {money(calculo.valor_inicial)} / {String(calculo.memoria_calculo.coeficiente).replace('.', ',')}</p>
      </>}
      {calculo?.memoria_calculo?.demonstrativa && calculo.memoria_calculo.aviso_demo && <p className="hint">{calculo.memoria_calculo.aviso_demo}</p>}
      {calculo?.memoria_calculo?.correspondencia_cadastral_confirmada === false && <p>Regra vigente do prefixo aplicada aos dados documentais confirmados; correspondência cadastral pendente.</p>}
      {calculo?.memoria_calculo && (
        <details>
          <summary>Ver detalhes do cálculo</summary>
          <p>Regra #{calculo.id_regra} · {calculo.memoria_calculo.estrategia} · Coeficiente: {String(calculo.memoria_calculo.parametros.coeficiente ?? 'Não se aplica')}</p>
          <p>
            Valor base: {money(calculo.memoria_calculo.valor_base)} · Resultado:{" "}
            {money(calculo.memoria_calculo.resultado)}
          </p>
          {calculo.memoria_calculo.componentes_considerados.map((c) => (
            <p key={c.id}>
              {c.tipo}: {c.operacao} {money(c.valor)}
            </p>
          ))}
        </details>
      )}
    </section>
  );
}
export function EditInvoiceModal({
  dados,
  itens,
  busy,
  error,
  onClose,
  onSave,
}: {
  dados: DadoExtraido[];
  itens: ItemExtraido[];
  busy: boolean;
  error: string;
  onClose: () => void;
  onSave: (values: Record<string, string>) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries([
      ...dados.map((d) => [
        "d" + d.id_dado_extraido,
        d.campo_identificado === "competencia" ? formatCompetenciaDisplay(d.valor_validado ?? d.valor_normalizado ?? d.valor_extraido ?? "") : d.valor_validado ?? d.valor_normalizado ?? d.valor_extraido ?? "",
      ]),
      ...itens.map((i) => [
        "i" + i.id_item_extraido,
        String(i.valor_validado ?? i.valor),
      ]),
    ]),
  );
  const ref = (element: HTMLDialogElement | null) => {
    if (element && !element.open) element.showModal();
  };
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      aria-labelledby="edit-title"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSave(values);
        }}
      >
        <h2 id="edit-title">Ajustar dados da fatura</h2>
        <p>
          As correções são salvas como valores validados. Os valores originais
          são preservados.
        </p>
        <div className="modal-scroll">
          {dados.map((d) => (
            <label key={d.id_dado_extraido}>
              {labels[d.campo_identificado] ??
                d.campo_identificado.replaceAll("_", " ")}
              <input
                aria-label={labels[d.campo_identificado] ?? d.campo_identificado.replaceAll("_", " ")}
                autoFocus={d === dados[0]}
                type={
                  d.campo_identificado === "data_vencimento"
                    ? "date"
                    : d.campo_identificado === "competencia"
                      ? "text"
                      : ["valor_original", "consumo"].includes(
                            d.campo_identificado,
                          )
                        ? "number"
                        : "text"
                }
                placeholder={d.campo_identificado === "competencia" ? "MM/AAAA" : undefined}
                pattern={d.campo_identificado === "competencia" ? "(0[1-9]|1[0-2])/[0-9]{4}" : undefined}
                step="any"
                value={values["d" + d.id_dado_extraido]}
                onChange={(e) =>
                  setValues({
                    ...values,
                    ["d" + d.id_dado_extraido]: e.target.value,
                  })
                }
              />
              <small>Extraído: {d.valor_extraido ?? "Não informado"}</small>
            </label>
          ))}
          {itens.length > 0 && <h3>Composição da fatura</h3>}
          {itens.map((i) => (
            <label key={i.id_item_extraido}>
              {itemLabels[i.tipo_normalizado] ?? i.tipo_normalizado.replaceAll("_", " ")}
              <input
                required
                type="number"
                min="0"
                step="0.01"
                value={values["i" + i.id_item_extraido]}
                onChange={(e) =>
                  setValues({
                    ...values,
                    ["i" + i.id_item_extraido]: e.target.value,
                  })
                }
              />
              <small>Original: {money(i.valor)}</small>
            </label>
          ))}
        </div>
        {error && (
          <p className="notice error" role="alert">
            {error}
          </p>
        )}
        <div className="actions">
          <button type="button" disabled={busy} onClick={onClose}>
            Cancelar
          </button>
          <button className="primary" disabled={busy}>
            {busy ? "Salvando…" : "Salvar alterações"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
export function ConfirmationCard({
  situacao,
  fields,
  calculo,
  onReset,
}: {
  situacao?: string;
  fields: SummaryField[];
  calculo: Calculo;
  onReset: () => void;
}) {
  return (
    <section className="card confirmation">
      <div className="success-icon">✓</div>
      <h2>Processamento concluído</h2>
      <p>{situacao === "confirmada_checker" ? "Confirmação final registrada pelo Checker." : situacao === "rejeitada_checker" ? "Fatura rejeitada pelo Checker. Consulte a decisão na área Checker." : "Fatura pronta para conferência e confirmação final pelo Checker."}</p>
      <p>Esta demonstração não realiza pagamento bancário.</p>
      <InvoiceSummary
        fields={[{ label: calculo.id_calculo ? "Identificador do cálculo" : "Identificador da leitura", value: String(calculo.id_calculo ?? ("id_extracao" in calculo ? calculo.id_extracao : "")) }, { label: "Valor calculado", value: money(calculo.valor_calculado) }, { label: "Data/hora do cálculo", value: new Date(calculo.data_calculo + (/Z$|[+-]\d{2}:\d{2}$/.test(calculo.data_calculo) ? "" : "Z")).toLocaleString("pt-BR") }, ...fields.filter((f) =>
          [
            "Tipo da fatura",
            "Concessionária",
            "Competência",
            "Valor da fatura",
          ].includes(f.label),
        )]}
      />
      <CalculationSummary calculo={calculo} />
      <button className="primary" onClick={onReset}>
        Nova fatura
      </button>
    </section>
  );
}
