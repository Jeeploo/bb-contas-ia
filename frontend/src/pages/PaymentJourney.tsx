import { ValidationSummary } from "../components/payment/ValidationSummary";
import { useAuth } from "../auth/AuthContext";
import { useState } from "react";
import { parseCompetenciaDisplay } from "../utils/competencia";
import { api } from "../api";
import { errorMessage } from "../api/client";
import { money } from "../components/ui";
import {
  PaymentStepper,
  ProcessingState,
} from "../components/payment/PaymentStepper";
import { UploadArea } from "../components/payment/UploadArea";
import {
  InvoiceSummary,
  DocumentPreview,
  EditInvoiceModal,
  ConfirmationCard,
  CalculationSummary,
  labels,
  documentaryMessages,
  itemLabels,
} from "../components/payment/InvoiceSummary";
import type { ProcessamentoDocumento, Calculo, Documento } from "../types";
export function PaymentJourney() {
  const { session, changingPrefix, selectPrefix } = useAuth();
  const [step, setStep] = useState(1);
  const [file, setFile] = useState<File>();
  const [doc, setDoc] = useState<Documento>();
  const [result, setResult] = useState<ProcessamentoDocumento>();
  const [calculo, setCalculo] = useState<Calculo>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const prefixos = session?.prefixos ?? [];
  const selectedPrefix = prefixos.find(p=>p.id_prefixo === session?.id_prefixo_ativo);
  const accountId = result?.documento.id_conta;
  async function process() {
    if (!file || !selectedPrefix || changingPrefix) return;
    setError("");
    setBusy(true);
    try {
      const uploaded = doc ?? (await api.uploadInicial(file));
      setDoc(uploaded);
      const response = await api.processarInteligente(uploaded.id_documento);
      setResult(response);
      setCalculo(undefined);
      setStep(2);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function validate(values?: Record<string, string>) {
    if (!result) return;
    setBusy(true);
    setError("");
    setCalculo(undefined);
    try {
      const campos = [];
      for (const d of result.campos_encontrados) {
        const value = values?.["d" + d.id_dado_extraido] ?? d.valor_validado ?? d.valor_normalizado ?? d.valor_extraido ?? "";
        const updated = await api.validar(d.id_dado_extraido,
          d.campo_identificado === "competencia" ? parseCompetenciaDisplay(value) : value);
        campos.push(updated);
        setResult((old) =>
          old
            ? {
                ...old,
                campos_encontrados: old.campos_encontrados.map((x) =>
                  x.id_dado_extraido === updated.id_dado_extraido ? updated : x,
                ),
              }
            : old,
        );
      }
      const itens = [];
      for (const i of result.itens_encontrados) {
        const updated = await api.validarItem(
          i.id_item_extraido,
          values?.["i" + i.id_item_extraido] ??
            String(i.valor_validado ?? i.valor),
        );
        itens.push(updated);
        setResult((old) =>
          old
            ? {
                ...old,
                itens_encontrados: old.itens_encontrados.map((x) =>
                  x.id_item_extraido === updated.id_item_extraido ? updated : x,
                ),
              }
            : old,
        );
      }
      // Recupera a decisão e o vínculo após as correções, sem chamar a IA novamente.
      const [extracao, documento] = await Promise.all([
        api.extracoes().then((all) => all.find((e) => e.id_extracao === result.extracao.id_extracao)),
        api.documentos().then((all) => all.find((d) => d.id_documento === result.documento.id_documento)),
      ]);
      const reviewed = { ...result, campos_encontrados: campos, itens_encontrados: itens,
        extracao: extracao ?? result.extracao, documento: documento ?? result.documento };
      setResult(reviewed);
      setEditing(false);
      if (!values) {
        if (!reviewed.documento.id_conta || reviewed.extracao.resultado_validacao_documental !== "VALIDO") {
          setError("Confira a validação cadastral antes de continuar. O documento permanece em revisão.");
          return;
        }
        setCalculo(await api.calcular(reviewed.documento.id_conta));
        setStep(3);
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  const fields = (() => {
    const values = new Map<string, string>();
    if (selectedPrefix) values.set("Prefixo", `${selectedPrefix.codigo_prefixo} — ${selectedPrefix.nome}`);
    for (const d of result?.campos_encontrados ?? []) {
      const value = d.valor_validado ?? d.valor_normalizado ?? d.valor_extraido;
      const label = labels[d.campo_identificado];
      if (value && label)
        values.set(
          label,
          ["valor_original", "valor_total"].includes(d.campo_identificado) ? money(value) : value,
        );
    }
    const unit = values.get("Unidade de consumo");
    if (unit && values.has("Consumo")) { values.set("Consumo", `${values.get("Consumo")} ${unit}`); values.delete("Unidade de consumo"); }
    const order = ["Tipo da fatura", "Valor da fatura", "Data de vencimento", "Competência", "Prefixo", "Concessionária", "Unidade consumidora", "Consumo", "Código de barras", "Município", "UF"];
    return [...values].sort(([a], [b]) => (order.includes(a) ? order.indexOf(a) : order.length) - (order.includes(b) ? order.indexOf(b) : order.length)).map(([label, value]) => ({ label, value }));
  })();
  function reset() {
    setStep(1);
    setFile(undefined);
    setDoc(undefined);
    setResult(undefined);
    setCalculo(undefined);
    setError("");
  }
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">PAGAMENTOS</span>
          <h1>Pagamento de faturas</h1>
          <p>Registre sua fatura de água e energia de forma simples e rápida</p>
        </div>
      </div>
      <PaymentStepper step={step} />
      {error && !editing && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {step === 1 &&
        (busy ? (
          <ProcessingState received={!!doc} />
        ) : (
          <section className="card upload-card">
            <div className="upload-heading"><span className="section-number">1</span><div><h2>Upload da fatura</h2><p>Envie uma imagem ou PDF para leitura automática dos dados</p></div></div>
            <UploadArea file={file} onChange={(f) => { setFile(f); setDoc(undefined); setError(""); }} />
            <p className="upload-hint">Use um documento com boa qualidade para melhorar a leitura automática.</p>
            {prefixos.length === 1 ? <p>Prefixo: {selectedPrefix?.codigo_prefixo} — {selectedPrefix?.nome}</p> : <label>Prefixo
              <select aria-label="Prefixo" disabled={changingPrefix} value={selectedPrefix?.id_prefixo ?? ""} onChange={async (e) => {
                setDoc(undefined); setError("");
                try { await selectPrefix(Number(e.target.value)); } catch (err) { setError(errorMessage(err)); }
              }}>
                <option value="" disabled>Selecione um prefixo autorizado</option>
                {prefixos.map(p=><option key={p.id_prefixo} value={p.id_prefixo}>{p.codigo_prefixo} — {p.nome}</option>)}
              </select>
            </label>}
            {!prefixos.length && <p>Nenhum prefixo ativo autorizado.</p>}
            <div className="actions">
              <button
                className="primary"
                disabled={!file || !selectedPrefix || changingPrefix}
                onClick={() => void process()}
              >
                Iniciar processamento
              </button>
            </div>
          </section>
        ))}
      {step === 2 && result && (
        <>
          <section className="card summary-card"><div className="review-grid">
            <DocumentPreview file={file} />
            <section className="summary-content">
              <div className="section-heading">
                <h2>Resumo da fatura</h2>
                <button
                  disabled={busy}
                  onClick={() => {
                    setError("");
                    setEditing(true);
                  }}
                >
                  Editar dados
                </button>
              </div>
              {result.campos_encontrados.length ? (
                <><InvoiceSummary fields={fields} /><p className="hint">Dados extraídos automaticamente, pendentes de confirmação.</p>{calculo && <CalculationSummary calculo={calculo} />}</>
              ) : (
                <p>
                  Nenhum campo extraído. Envie outro documento com dados
                  legíveis.
                </p>
              )}
              <p className="notice" role="status">{documentaryMessages[result.extracao.resultado_validacao_documental ?? "EVIDENCIA_INSUFICIENTE"]}</p>
              <p>Correspondência cadastral da concessionária: {result.extracao.evidencias_validacao_documental?.id_concessionaria ? "encontrada" : "não encontrada — revisão necessária"}</p>
              {result.itens_encontrados.length > 0 && (
                <details>
                  <summary>
                    Revisar composição da fatura (
                    {result.itens_encontrados.length})
                  </summary>
                  {result.itens_encontrados.map((i) => (
                    <p key={i.id_item_extraido}>
                      {itemLabels[i.tipo_normalizado] ?? i.tipo_normalizado.replaceAll("_", " ")}:{" "}
                      {money(i.valor_validado ?? i.valor)}
                    </p>
                  ))}
                </details>
              )}
              <p className="hint">Confirme os dados extraídos antes de continuar. O cálculo exige correspondência cadastral e validação documental.</p>
            </section>
          </div>
          <div className="actions">
            <button disabled={busy} onClick={reset}>
              Refazer leitura
            </button>
            <button
              className="primary"
              disabled={busy || !result.campos_encontrados.length || !accountId || result.extracao.resultado_validacao_documental !== "VALIDO"}
              onClick={() => void validate()}
            >
              {busy ? "Validando e calculando…" : "Enviar para validação"}
            </button>
          </div>
        </section>
        </>
      )}
      {step === 3 && calculo && (
        <ValidationSummary fields={fields} calculo={calculo} onBack={() => setStep(2)} onConfirm={() => setStep(4)} />
      )}
      {step === 4 && calculo && (
        <ConfirmationCard fields={fields} calculo={calculo} onReset={reset} />
      )}
      {editing && result && (
        <EditInvoiceModal
          dados={result.campos_encontrados}
          itens={result.itens_encontrados}
          busy={busy}
          error={error}
          onClose={() => {
            setEditing(false);
            setError("");
          }}
          onSave={(v) => void validate(v)}
        />
      )}
    </>
  );
}
