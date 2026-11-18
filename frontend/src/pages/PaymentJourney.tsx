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
import { ResumoCampos, ResumoLista, type ResumoCampo } from "../components/payment/ResumoCampos";
import { DocumentViewer } from "../components/payment/DocumentViewer";
import { MapaRegiao } from "../components/payment/MapaRegiao";
import { isDevBypass } from "../config/devBypass";
import { ArrowLeft, ChevronRight, Pencil } from "lucide-react";
import {
  InvoiceSummary,
  EditInvoiceModal,
  ConfirmationCard,
  CalculationSummary,
  labels,
  itemLabels,
} from "../components/payment/InvoiceSummary";
import type { ProcessamentoDocumento, ResultadoCalculo as Calculo, Documento, JornadaPersistida } from "../types";
const RESUMO_LABELS = ["Tipo da fatura", "Valor da fatura", "Data de vencimento", "Prefixo", "Unidade/Agência", "Agência", "Concessionária", "Código de barras"];
// Campo(s) extraído(s) que o lápis de cada card abre na edição.
const CAMPOS_EDICAO: Record<string, string[]> = {
  "Tipo da fatura": ["tipo_documento", "categoria", "tipo_servico"], "Valor da fatura": ["valor_total", "valor_original"],
  "Data de vencimento": ["data_vencimento"], "Concessionária": ["concessionaria"], "Código de barras": ["codigo_barras"], "Agência": ["agencia"],
};
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
  const [editFocus, setEditFocus] = useState<string[]>();
  function openEdit(campos?: string[]) { setError(""); setEditFocus(campos); setEditing(true); }
  // Navegação entre etapas: a etapa "derivada" vem dos dados (servidor/mock); o usuário pode
  // voltar (viewStep) sem perder nada. maxReached guarda a etapa mais avançada já alcançada.
  const derivedStep = journeyStep(result?.extracao, calculo);
  const [viewStep, setViewStep] = useState<number>();
  const [maxReached, setMaxReached] = useState(1);
  const reachable = Math.max(maxReached, derivedStep);
  const step = Math.min(viewStep ?? derivedStep, reachable);
  useEffect(() => { setMaxReached(m => Math.max(m, derivedStep)); }, [derivedStep]);
  // Fatura já processada (etapa 4 alcançada): etapas anteriores ficam somente para consulta.
  const locked = reachable >= 4;
  // "Desatualizado": versão dos dados × versão com que a validação e o cálculo foram feitos.
  const dataVersion = useRef(0);
  const validatedVersion = useRef<number | undefined>(undefined);
  const calculatedVersion = useRef<number | undefined>(undefined);
  function resetNavigation(validated?: boolean, calculated?: boolean) {
    setViewStep(undefined); setMaxReached(1);
    dataVersion.current = 0;
    validatedVersion.current = validated ? 0 : undefined;
    calculatedVersion.current = calculated ? 0 : undefined;
  }
  // Vai para uma etapa já alcançada; se ela estiver desatualizada, refaz validação/cálculo antes.
  async function goTo(target: number) {
    if (target < 1 || target > reachable || busy) return;
    setError("");
    if (!(await ensureFresh(target))) return;
    setViewStep(target);
  }
  async function ensureFresh(target: number) {
    if (locked || !result || target < 3) return true;
    const v = dataVersion.current;
    if (validatedVersion.current !== v && !(await validate())) return false;
    if (target === 4 && calculatedVersion.current !== v && !(await calculate())) return false;
    return true;
  }
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
    resetNavigation();
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
      resetNavigation(journeyStep(j.processamento?.extracao, j.calculo ?? undefined) >= 3, !!j.calculo);
    }).catch(e => { if (active) { setError(errorMessage(e)); setRestoreFailed(true); } })
      .finally(() => {
        if (restoreRequest.current === pending) restoreRequest.current = null;
        if (active) setRestoring(false);
      });
    return () => { active = false; };
  }, [session?.usuario.id_usuario, session?.id_prefixo_ativo, restoreAttempt, needsPrefix]);
  async function process(nextFile?: File) {
    // nextFile = arquivo trocado na etapa 1: força novo upload e nova leitura.
    const sourceFile = nextFile ?? file;
    const currentDoc = nextFile ? undefined : doc;
    if ((!sourceFile && !currentDoc) || !selectedPrefix || changingPrefix || busy) return;
    setProcessingAttempt(attempt => attempt + 1);
    setProcessingPhase('uploading');
    setProcessingVisible(true);
    setProcessedResult(undefined);
    setError("");
    setBusy(true);
    try {
      const uploaded = currentDoc ?? (await api.uploadInicial(sourceFile!));
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
    dataVersion.current += 1;   // nova leitura: validação/cálculo anteriores ficam desatualizados
    setViewStep(undefined);
  }
  async function validate(values?: Record<string, string>): Promise<boolean> {
    if (!result) return false;
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
      if (values) {
        // Edição: etapas seguintes ficam desatualizadas; continua na etapa atual.
        dataVersion.current += 1;
        setViewStep(step);
      } else {
        validatedVersion.current = dataVersion.current;
        calculatedVersion.current = undefined;
        setViewStep(undefined);
      }
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function saveEdit(values: Record<string, string>) {
    if (!(await validate(values))) return;
    // Editou na etapa 3: refaz a validação com os dados novos e continua nela.
    if (step >= 3 && (await ensureFresh(step))) setViewStep(step);
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
  async function calculate(): Promise<boolean> {
    if (!result || result.extracao.bloqueia_calculo) return false;
    setBusy(true); setError('');
    try {
      await api.calcularDocumento(result.documento.id_documento);
      const restored = await api.jornadaDocumento(result.documento.id_documento);
      setResult(restored.processamento ?? undefined); setCalculo(restored.calculo ?? undefined);
      calculatedVersion.current = dataVersion.current;
      setViewStep(undefined);
      return true;
    } catch (e) { setError(errorMessage(e)); return false; } finally { setBusy(false); }
  }
  const fields = (() => {
    const values = new Map<string, string>();
    if (selectedPrefix) values.set("Prefixo", selectedPrefix.codigo_prefixo);
    for (const d of result?.campos_encontrados ?? []) {
      const value = d.valor_validado ?? d.valor_normalizado ?? d.valor_extraido;
      const label = labels[d.campo_identificado];
      if (value && label)
        values.set(
          label,
          ["valor_original", "valor_total"].includes(d.campo_identificado) ? money(value) : value,
        );
    }
    if (selectedPrefix) values.set("Prefixo", selectedPrefix.codigo_prefixo);
    values.set("Unidade/Agência", selectedPrefix?.nome ?? values.get("Unidade consumidora") ?? "Não informado");
    const unit = values.get("Unidade de consumo");
    if (unit && values.has("Consumo")) { values.set("Consumo", `${values.get("Consumo")} ${unit}`); values.delete("Unidade de consumo"); }
    for (const label of ["Tipo da fatura", "Valor da fatura", "Data de vencimento", "Prefixo", "Unidade/Agência", "Concessionária", "Código de barras"]) if (!values.has(label)) values.set(label, "Não informado");
    const order = ["Tipo da fatura", "Valor da fatura", "Data de vencimento", "Competência", "Prefixo", "Unidade/Agência", "Concessionária", "Unidade consumidora", "Consumo", "Código de barras", "Município", "UF"];
    return [...values].sort(([a], [b]) => (order.includes(a) ? order.indexOf(a) : order.length) - (order.includes(b) ? order.indexOf(b) : order.length)).map(([label, value]) => ({ label, value }));
  })();
  const valorDe = (label: string) => fields.find(f => f.label === label)?.value;
  const informado = (v?: string) => v && v !== "Não informado" ? v : undefined;
  const agencia = (informado(valorDe("Agência")) ?? selectedPrefix?.codigo_prefixo ?? "Não informado").replace(/prefixo\s*/i, "");
  const resumoCampos: ResumoCampo[] = ([
    ["Tipo da fatura", valorDe("Tipo da fatura")], ["Prefixo", selectedPrefix?.codigo_prefixo],
    ["Valor da fatura", valorDe("Valor da fatura")], ["Agência", agencia],
    ["Data de vencimento", valorDe("Data de vencimento")], ["Concessionária", valorDe("Concessionária")],
    ["Código de barras", valorDe("Código de barras")],
  ] as [string, string | undefined][]).map(([label, value]) => ({ label, value: value ?? "Não informado", onEdit: () => openEdit(CAMPOS_EDICAO[label]) }));
  // Etapa 3: mesmos dados do Resumo (com as edições do usuário).
  const resumoValidacao = [
    { label: "Tipo da fatura", titulo: "Tipo de fatura", value: valorDe("Tipo da fatura") ?? "Não informado" },
    { label: "Concessionária", value: valorDe("Concessionária") ?? "Não informado" },
    { label: "Valor da fatura", value: valorDe("Valor da fatura") ?? "Não informado" },
    { label: "Data de vencimento", titulo: "Vencimento", value: valorDe("Data de vencimento") ?? "Não informado" },
    { label: "Unidade", value: `${selectedPrefix?.codigo_prefixo ?? "—"} / ${agencia}` },
    { label: "Responsável", value: session?.usuario.nome ?? "Não informado" },
  ];
  // Cidade/UF vêm da fatura; sem esses dados, o modo DEV usa Recife - PE.
  const localidade = {
    cidade: informado(valorDe("Município")) ?? (isDevBypass() ? "Recife" : undefined),
    uf: informado(valorDe("UF")) ?? (isDevBypass() ? "PE" : undefined),
  };
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
    resetNavigation();
  }
  return (
    <>
      <div className="page-title payment-title">
        <div>
          <span className="eyebrow">PAGAMENTOS</span>
          <h1>Pagamento de faturas</h1>
          <p>Registre sua fatura de água e energia de forma simples e rápida</p>
        </div>
        <button disabled={busy || restoring} onClick={() => void reset()}>Nova fatura</button>
      </div>
      <PaymentStepper step={step} reached={reachable} onSelect={n => void goTo(n)} />
      {locked && step < 4 && <p className="journey-locked" role="status">Esta fatura já foi processada. Para alterar, inicie uma Nova fatura.</p>}
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
            {doc && !file && <p>Documento #{doc.id_documento} recuperado. Continue a leitura sem reenviar o arquivo.</p>}
            {!locked && (!doc || file) && <UploadArea file={file} onChange={(f) => {
              setError("");
              // Trocou o arquivo depois de já ter lido um: refaz a leitura com o novo.
              if (f && result && f !== file) { setFile(f); setDoc(undefined); void process(f); }
              else setFile(f);
            }} />}
            {result && (file || doc) && <div className="upload-preview"><DocumentViewer file={file} documentId={doc?.id_documento ?? result.documento.id_documento} documentFormat={doc?.formato ?? result.documento.formato} /></div>}
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
              {result && doc ? (
                <button className="primary" disabled={busy} onClick={() => void goTo(2)}>
                  Avançar <ChevronRight size={16} aria-hidden="true" />
                </button>
              ) : (
                <button
                  className="primary"
                  disabled={(!file && !doc) || !selectedPrefix || changingPrefix}
                  onClick={() => void process()}
                >
                  Iniciar processamento
                </button>
              )}
            </div>
          </section>
        ))}
      {result?.extracao.historico_validacao_documental?.some(h => ["ENVIADO_MAKER","REENVIADO","CORRIGIDO_MAKER","DECISAO_CHECKER"].includes(String(h.evento))) && <details className="card"><summary>Histórico da revisão</summary>{result.extracao.historico_validacao_documental?.filter(h => ["ENVIADO_MAKER","REENVIADO","CORRIGIDO_MAKER","DECISAO_CHECKER"].includes(String(h.evento))).map((h,i)=><p key={i}>{String(h.data)} · {({ENVIADO_MAKER:"Enviado pelo Maker", REENVIADO:"Reenviado pelo Maker", CORRIGIDO_MAKER:"Corrigido pelo Maker", DECISAO_CHECKER:h.decisao === "aprovado" ? "Aprovado pelo Checker" : "Devolvido pelo Checker"} as Record<string,string>)[String(h.evento)]} · {String(h.usuario_nome ?? "")} {String(h.motivo ?? "")} {String(h.observacao ?? "")}</p>)}</details>}
      {result?.extracao.situacao_validacao === "rejeitada_checker" && <Alert variant="error"><strong>Devolvida pelo Checker</strong><p>Motivo: {String(result.extracao.historico_validacao_documental?.slice().reverse().find(h => h.evento === "DECISAO_CHECKER")?.motivo ?? "")} — {String(result.extracao.historico_validacao_documental?.slice().reverse().find(h => h.evento === "DECISAO_CHECKER")?.observacao ?? "")}</p></Alert>}
      {step === 2 && result && (
        <section className="card summary-card resumo-card">
          <div className="resumo-corpo">
            <div className="resumo-esquerda">
              <div className="upload-heading resumo-heading"><span className="section-number">2</span><div><h2>Resumo da fatura</h2><p>Confira os dados extraídos e analise a unidade antes de enviar para validação</p></div></div>
              {result.campos_encontrados.length
                ? <ResumoCampos campos={resumoCampos} readOnly={locked} />
                : <p>Nenhum campo extraído. Envie outro documento com dados legíveis.</p>}
            </div>
            <DocumentViewer file={file} documentId={result.documento.id_documento} documentFormat={result.documento.formato} />
          </div>
          <section className="summary-content resumo-extras">
            {result.campos_encontrados.length > 0 && <><details><summary>Ver detalhes</summary><InvoiceSummary fields={fields.filter(f => !RESUMO_LABELS.includes(f.label))} /></details><p className="hint">Dados extraídos automaticamente, pendentes de confirmação.</p>{calculo && <CalculationSummary calculo={calculo} />}</>}
            {result.extracao.situacao_validacao === "revisao_cadastral_pendente" && <Alert variant="info"><strong>Documento enviado para validação</strong><p>Revisão cadastral pendente. Pendência que não impede continuar.</p></Alert>}
            <details open={result.extracao.bloqueia_calculo}><summary>Pendências e alertas — conferir ({result.extracao.pendencias?.length ?? 0})</summary><DocumentaryAlerts confirmado={result.campos_encontrados.every(f => f.situacao_validacao === "validada")} extracao={result.extracao} concessionaria={fields.find(f => f.label === "Concessionária")?.value} /></details>
            {result.itens_encontrados.length > 0 && (
              <details>
                <summary>Revisar composição da fatura ({result.itens_encontrados.length})</summary>
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
          <div className="actions">
            <button className="journey-back" disabled={busy} onClick={() => void goTo(1)}><ArrowLeft size={16} aria-hidden="true" /> Voltar</button>
            <button className="resumo-btn-secundario" disabled={busy || locked} onClick={() => openEdit()}>
              <Pencil size={15} aria-hidden="true" /> Editar dados
            </button>
            {reachable > 2 ? (
              <button className="primary" disabled={busy} onClick={() => void goTo(3)}>
                {busy ? "Atualizando…" : "Avançar"} <ChevronRight size={16} aria-hidden="true" />
              </button>
            ) : (
              <button
                className="primary"
                disabled={busy || !result.campos_encontrados.length || !canSubmitReview(result.extracao)}
                onClick={() => void validate()}
              >
                {busy ? "Enviando para validação…" : result.extracao.situacao_validacao === "revisao_cadastral_pendente" ? "Enviado para validação" : "Enviar para validação"} <ChevronRight size={16} aria-hidden="true" />
              </button>
            )}
          </div>
        </section>
      )}
      {step === 3 && result && <><ConcessionariaReview extracao={result.extracao}
        nome={result.campos_encontrados.find(f => f.campo_identificado === 'concessionaria')?.valor_extraido ?? undefined}
        busy={busy || locked} onAssociate={() => void openAssociation()} onCalculate={() => void calculate()}
        footerStart={<button className="journey-back" disabled={busy} onClick={() => void goTo(2)}><ArrowLeft size={16} aria-hidden="true" /> Voltar</button>}
        footerEnd={reachable > 3 ? <button className="primary" disabled={busy} onClick={() => void goTo(4)}>{busy ? "Atualizando…" : "Avançar"} <ChevronRight size={16} aria-hidden="true" /></button> : undefined}>
        <ResumoLista linhas={resumoValidacao} />
        <DocumentViewer file={file} documentId={result.documento.id_documento} documentFormat={result.documento.formato} />
        <MapaRegiao cidade={localidade.cidade} uf={localidade.uf} />
      </ConcessionariaReview></>}
      {associating && result && <AssociarConcessionariaModal
        nome={result.campos_encontrados.find(f => f.campo_identificado === 'concessionaria')?.valor_extraido ?? undefined}
        opcoes={opcoes} selected={selected} busy={associationBusy} error={associationError} onSelect={setSelected}
        onClose={() => {setAssociating(false); setAssociationError('');}} onConfirm={() => void associate()} />}
      {step === 4 && calculo && (
        <><ConfirmationCard fields={fields} calculo={calculo} situacao={result?.extracao.situacao_validacao} onReset={() => void reset()}
          footerStart={<button className="journey-back" disabled={busy} onClick={() => void goTo(3)}><ArrowLeft size={16} aria-hidden="true" /> Voltar</button>} />
        {result && <DocumentaryAlerts extracao={result.extracao} confirmado />}</>
      )}
      {editing && result && (
        <EditInvoiceModal
          dados={result.campos_encontrados}
          itens={result.itens_encontrados}
          focusCampos={editFocus}
          busy={busy}
          error={error}
          onClose={() => {
            setEditing(false);
            setError("");
          }}
          onSave={(v) => void saveEdit(v)}
        />
      )}
    </>
  );
}
