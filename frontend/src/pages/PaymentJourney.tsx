import { ProcessingState } from '../components/payment/ProcessingState';
import type { ProcessingPhase } from '../utils/processingProgress';
import { journeyStep } from '../utils/journey';
import { ConcessionariaReview, AssociarConcessionariaModal, type OpcaoConcessionaria } from '../components/payment/ConcessionariaReview';
import { Alert, DocumentaryAlerts, canSubmitReview } from "../components/payment/DocumentaryAlerts";
import { useAuth } from "../auth/AuthContext";
import { useEffect, useRef, useState } from "react";
import { parseCompetenciaDisplay } from "../utils/competencia";
import { api } from "../api";
import { errorMessage } from "../api/client";
import { money } from "../components/ui";
import {
  PaymentStepper,
} from "../components/payment/PaymentStepper";
import { UploadArea } from "../components/payment/UploadArea";
import {
  InvoiceSummary,
  DocumentPreview,
  EditInvoiceModal,
  ConfirmationCard,
  CalculationSummary,
  labels,
  itemLabels,
} from "../components/payment/InvoiceSummary";
import type { ProcessamentoDocumento, ResultadoCalculo as Calculo, Documento, JornadaPersistida } from "../types";
export function PaymentJourney() {
  const { session, changingPrefix, selectPrefix } = useAuth();
  const [restoreFailed, setRestoreFailed] = useState(false);
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const [restoring, setRestoring] = useState(true);
  const [associating, setAssociating] = useState(false);
  const [associationBusy, setAssociationBusy] = useState(false);
  const [associationError, setAssociationError] = useState("");
  const [opcoes, setOpcoes] = useState<OpcaoConcessionaria[]>([]);
  const [selected, setSelected] = useState(0);
  const [file, setFile] = useState<File>();
  const [doc, setDoc] = useState<Documento>();
  const [result, setResult] = useState<ProcessamentoDocumento>();
  const [calculo, setCalculo] = useState<Calculo>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [processingPhase, setProcessingPhase] = useState<ProcessingPhase>('uploading');
  const [processingAttempt, setProcessingAttempt] = useState(0);
  const [processingVisible, setProcessingVisible] = useState(false);
  const [processedResult, setProcessedResult] = useState<ProcessamentoDocumento>();
  const [editing, setEditing] = useState(false);
  const step = journeyStep(result?.extracao, calculo);
  const prefixos = session?.prefixos ?? [];
  const selectedPrefix = prefixos.find(p=>p.id_prefixo === session?.id_prefixo_ativo);
  const needsPrefix = prefixos.length > 1 && !session?.id_prefixo_ativo;
  const restoreRequest = useRef<{ key: string; promise: Promise<JornadaPersistida> } | null>(null);
  useEffect(() => {
    let active = true;
    setRestoring(true); setRestoreFailed(false);
    setResult(undefined); setCalculo(undefined); setDoc(undefined); setFile(undefined);
    setProcessingVisible(false); setBusy(false); setError('');
    setAssociating(false); setAssociationError('');
    if (needsPrefix) { setRestoring(false); return () => { active = false; }; }
    const key = `${session?.usuario.id_usuario}:${session?.id_prefixo_ativo}:${restoreAttempt}`;
    // Reutiliza a consulta em andamento durante a repetição de efeitos do StrictMode.
    if (!restoreRequest.current || restoreRequest.current.key !== key)
      restoreRequest.current = { key, promise: api.retomarJornada() };
    const pending = restoreRequest.current;
    pending.promise.then(j => {
      if (!active) return;
      setDoc(j.documento ?? undefined);
      setResult(j.processamento ?? undefined);
      setCalculo(j.calculo ?? undefined);
    }).catch(e => { if (active) { setError(errorMessage(e)); setRestoreFailed(true); } })
      .finally(() => {
        if (restoreRequest.current === pending) restoreRequest.current = null;
        if (active) setRestoring(false);
      });
    return () => { active = false; };
  }, [session?.usuario.id_usuario, session?.id_prefixo_ativo, restoreAttempt, needsPrefix]);
  async function process() {
    if ((!file && !doc) || !selectedPrefix || changingPrefix || busy) return;
    setProcessingAttempt(attempt => attempt + 1);
    setProcessingPhase('uploading');
    setProcessingVisible(true);
    setProcessedResult(undefined);
    setError("");
    setBusy(true);
    try {
      const uploaded = doc ?? (await api.uploadInicial(file!));
      setDoc(uploaded);
      setProcessingPhase('extracting');
      const response = await api.processarInteligente(uploaded.id_documento);
      setProcessingPhase('validating');
      setProcessedResult(response);
      setProcessingPhase('complete');
    } catch (e) {
      setError(errorMessage(e));
      setProcessingPhase('error');
      setBusy(false);
    }
  }
  function showProcessedSummary() {
    if (!processedResult) return;
    setResult(processedResult);
    setCalculo(undefined);
    setProcessingVisible(false);
    setBusy(false);
  }
  async function validate(values?: Record<string, string>) {
    if (!result) return;
    setBusy(true);
    setError("");
    setCalculo(undefined);
    try {
      const normalized = { ...values };
      for (const field of result.campos_encontrados) {
        const key = "d" + field.id_dado_extraido;
        if (field.campo_identificado === "competencia" && normalized[key] !== undefined)
          normalized[key] = parseCompetenciaDisplay(normalized[key]);
      }
      const restored = await api.confirmarJornada(result.documento.id_documento, normalized, !values);
      setDoc(restored.documento ?? undefined);
      setResult(restored.processamento ?? undefined);
      setCalculo(restored.calculo ?? undefined);
      setEditing(false);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function openAssociation() {
    setAssociationError(''); setSelected(0); setOpcoes([]); setAssociating(true); setAssociationBusy(true);
    try { setOpcoes(await api.concessionariasElegiveis()); }
    catch { setAssociationError('Associação cadastral não disponível no ambiente DEMO. A leitura e o processamento podem continuar normalmente.'); }
    finally { setAssociationBusy(false); }
  }
  async function associate() {
    if (!result || !selected) return;
    setAssociationBusy(true); setAssociationError('');
    try {
      const extracao = await api.resolverConcessionaria(result.extracao.id_extracao, selected);
      setResult({...result, extracao}); setAssociating(false);
    } catch (e) { setAssociationError(errorMessage(e)); } finally { setAssociationBusy(false); }
  }
  async function calculate() {
    if (!result || result.extracao.bloqueia_calculo) return;
    setBusy(true); setError('');
    try {
      await api.calcularDocumento(result.documento.id_documento);
      const restored = await api.jornadaDocumento(result.documento.id_documento);
      setResult(restored.processamento ?? undefined); setCalculo(restored.calculo ?? undefined);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
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
  async function reset() {
    setBusy(true); setError('');
    try {
      if (doc) await api.novaFatura(doc.id_documento);
    } catch (e) { setError(errorMessage(e)); setBusy(false); return; }
    setBusy(false); setProcessingVisible(false); setProcessedResult(undefined); setEditing(false);
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
      <div className="actions"><button disabled={busy || restoring} onClick={() => void reset()}>Nova fatura</button></div>
      <PaymentStepper step={step} />
      {restoring && <p role="status">Recuperando processamento…</p>}
      {restoreFailed && <button onClick={() => setRestoreAttempt(a => a + 1)}>Tentar recuperar processamento</button>}
      {error && !editing && !associating && !processingVisible && (
        <Alert variant="error">{error}</Alert>
      )}
      {!restoring && !restoreFailed && step === 1 &&
        (processingVisible ? (
          <ProcessingState key={processingAttempt} phase={processingPhase} received={!!doc} error={error}
            onComplete={showProcessedSummary} onRetry={() => void process()}
            onBack={() => void reset()} />
        ) : (
          <section className="card upload-card">
            <div className="upload-heading"><span className="section-number">1</span><div><h2>Upload da fatura</h2><p>Envie uma imagem ou PDF para leitura automática dos dados</p></div></div>
            {doc && <p>Documento #{doc.id_documento} recuperado. Continue a leitura sem reenviar o arquivo.</p>}
            {!doc && <UploadArea file={file} onChange={(f) => { setFile(f); setError(""); }} />}
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
                disabled={(!file && !doc) || !selectedPrefix || changingPrefix}
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
            <DocumentPreview file={file} documentId={result.documento.id_documento} documentFormat={result.documento.formato} />
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
              {result.extracao.situacao_validacao === "revisao_cadastral_pendente" && <Alert variant="info"><strong>Documento enviado para validação</strong><p>Revisão cadastral pendente. Pendência que não impede continuar.</p></Alert>}
              <DocumentaryAlerts confirmado={result.campos_encontrados.every(f => f.situacao_validacao === "validada")} extracao={result.extracao} concessionaria={fields.find(f => f.label === "Concessionária")?.value} />
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
              <p className="hint">Confirme os dados extraídos antes de continuar. Pendências cadastrais não impedem continuar. Erros documentais precisam ser corrigidos.</p>
            </section>
          </div>
          <div className="actions">
            <button disabled={busy} onClick={reset}>
              Nova fatura
            </button>
            <button
              className="primary"
              disabled={busy || !result.campos_encontrados.length || !canSubmitReview(result.extracao)}
              onClick={() => void validate()}
            >
              {busy ? "Enviando para validação…" : result.extracao.situacao_validacao === "revisao_cadastral_pendente" ? "Enviado para validação" : "Enviar para validação"}
            </button>
          </div>
        </section>
        </>
      )}
      {step === 3 && result && <><button disabled={busy} onClick={() => { setError(""); setEditing(true); }}>Editar dados</button><ConcessionariaReview extracao={result.extracao}
        nome={result.campos_encontrados.find(f => f.campo_identificado === 'concessionaria')?.valor_extraido ?? undefined}
        busy={busy} onAssociate={() => void openAssociation()} onCalculate={() => void calculate()} /></>}
      {associating && result && <AssociarConcessionariaModal
        nome={result.campos_encontrados.find(f => f.campo_identificado === 'concessionaria')?.valor_extraido ?? undefined}
        opcoes={opcoes} selected={selected} busy={associationBusy} error={associationError} onSelect={setSelected}
        onClose={() => {setAssociating(false); setAssociationError('');}} onConfirm={() => void associate()} />}
      {step === 4 && calculo && (
        <><ConfirmationCard fields={fields} calculo={calculo} situacao={result?.extracao.situacao_validacao} onReset={() => void reset()} />
        {result && <DocumentaryAlerts extracao={result.extracao} confirmado />}</>
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
