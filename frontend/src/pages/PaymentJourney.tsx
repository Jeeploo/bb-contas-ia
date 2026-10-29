import { ValidationSummary } from "../components/payment/ValidationSummary";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { errorMessage } from "../api/client";
import { useResource, money } from "../components/ui";
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
} from "../components/payment/InvoiceSummary";
import type { ProcessamentoDocumento, Calculo, Documento } from "../types";
const load = async () => {
  const [contas, prefixos, concessionarias] = await Promise.all([
    api.contas(),
    api.prefixos(),
    api.concessionarias(),
  ]);
  return { contas, prefixos, concessionarias };
};
export function PaymentJourney() {
  const r = useResource(load);
  const [params] = useSearchParams();
  const [id, setId] = useState(params.get("conta") ?? "");
  const [step, setStep] = useState(1);
  const [file, setFile] = useState<File>();
  const [doc, setDoc] = useState<Documento>();
  const [result, setResult] = useState<ProcessamentoDocumento>();
  const [calculo, setCalculo] = useState<Calculo>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const conta = r.data?.contas.find((c) => c.id_conta === Number(id));
  async function process() {
    if (!file || !conta) return;
    setError("");
    if (!/\.pdf$/i.test(file.name)) {
      setError(
        "O backend atual processa apenas PDF. Selecione uma versão PDF da fatura para continuar.",
      );
      return;
    }
    setBusy(true);
    try {
      const uploaded = doc ?? (await api.upload(conta.id_conta, file));
      setDoc(uploaded);
      const response = await api.processar(uploaded.id_documento);
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
    if (!result || !conta) return;
    setBusy(true);
    setError("");
    setCalculo(undefined);
    try {
      const campos = [];
      for (const d of result.campos_encontrados) {
        const updated = await api.validar(
          d.id_dado_extraido,
          values?.["d" + d.id_dado_extraido] ??
            d.valor_validado ??
            d.valor_extraido ??
            "",
        );
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
      setResult({
        ...result,
        campos_encontrados: campos,
        itens_encontrados: itens,
      });
      setEditing(false);
      setCalculo(await api.calcular(conta.id_conta));
      if (!values) setStep(3);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  const fields = (() => {
    if (!conta) return [];
    const values = new Map<string, string>();
    values.set("Tipo da fatura", conta.categoria);
    const p = r.data?.prefixos.find((p) => p.id_prefixo === conta.id_prefixo);
    if (p) values.set("Prefixo", p.codigo_prefixo);
    const c = r.data?.concessionarias.find(
      (c) => c.id_concessionaria === conta.id_concessionaria,
    );
    if (c) values.set("Concessionária", c.nome_fantasia ?? c.razao_social);
    for (const d of result?.campos_encontrados ?? []) {
      const value = d.valor_validado ?? d.valor_extraido;
      const label = labels[d.campo_identificado];
      if (value && label)
        values.set(
          label,
          d.campo_identificado === "valor_original" ? money(value) : value,
        );
    }
    return [...values].map(([label, value]) => ({ label, value }));
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
            <details className="reference-account" open={!!file && !conta}><summary>Vincular conta cadastrada{conta ? ` · ${conta.categoria} · ${conta.competencia}` : ""}</summary>
            {r.loading ? (
              <p role="status">Carregando contas…</p>
            ) : r.error ? (
              <div className="notice error" role="alert">
                {r.error}
                <button onClick={r.reload}>Tentar novamente</button>
              </div>
            ) : !r.data?.contas.length ? (
              <p>
                Nenhuma conta cadastrada. Cadastre uma conta de referência no
                ambiente para receber a fatura.
              </p>
            ) : (
              <label>
                Conta de referência
                <select
                  value={id}
                  onChange={(e) => {
                    setId(e.target.value);
                    setDoc(undefined);
                  }}
                >
                  <option value="">Selecione uma conta</option>
                  {r.data.contas.map((c) => (
                    <option key={c.id_conta} value={c.id_conta}>
                      {c.categoria} · {c.competencia} · Conta {c.id_conta}
                    </option>
                  ))}
                </select>
              </label>
            )}
            </details>
            <div className="actions">
              <button
                className="primary"
                disabled={!file || !conta}
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
                <><InvoiceSummary fields={fields} /><CalculationSummary calculo={calculo} /></>
              ) : (
                <p>
                  Nenhum campo extraído. Envie outro documento com dados
                  legíveis.
                </p>
              )}
              {result.itens_encontrados.length > 0 && (
                <details>
                  <summary>
                    Revisar composição da fatura (
                    {result.itens_encontrados.length})
                  </summary>
                  {result.itens_encontrados.map((i) => (
                    <p key={i.id_item_extraido}>
                      {i.descricao_original}:{" "}
                      {money(i.valor_validado ?? i.valor)}
                    </p>
                  ))}
                </details>
              )}
              <p className="hint">
                Ao continuar, você confirma os dados e a composição
                apresentados. O cálculo será aplicado automaticamente.
              </p>
            </section>
          </div>
          <div className="actions">
            <button disabled={busy} onClick={reset}>
              Refazer leitura
            </button>
            <button
              className="primary"
              disabled={busy || !result.campos_encontrados.length}
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
