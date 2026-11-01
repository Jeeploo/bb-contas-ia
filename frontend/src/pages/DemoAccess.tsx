import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { errorMessage } from "../api/client";
import { useNavigate } from "react-router-dom";
import { LockKeyhole, ArrowRight, UserRound, Smartphone } from "lucide-react";
export function DemoAccess() {
  const auth = useAuth();
  const [matricula, setMatricula] = useState("");
  const [senha, setSenha] = useState("");
  const [fator, setFator] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit() {
    setError(""); setBusy(true);
    try { await auth.login(matricula, senha, fator); setSenha(""); setFator(""); navigate('/pagamentos', {replace:true}); }
    catch (e) { setError(errorMessage(e)); setSenha(""); setFator(""); }
    finally { setBusy(false); }
  }
  const navigate = useNavigate();
  return <div className="access-page">
    <header className="access-header"><img src="/assets/bb-logo.png" alt="Banco do Brasil" /><span>Gestão de contas de água e energia</span><small>Ambiente demonstrativo</small></header>
    <div className="access">
      <section className="access-intro">
        <img className="login-hero" src="/assets/login-hero.png" alt="Colaboradora em uma agência do Banco do Brasil" />
        <div className="access-message"><h1>Juntos<br />fazemos<br /><strong>mais pelo<br />amanhã.</strong></h1><p>Mais facilidade para cuidar das faturas.<br />Mais tempo para o que importa.</p></div>
      </section>
      <section className="access-form"><form className="access-card card" onSubmit={e => { e.preventDefault(); void submit(); }}>
        
        <span className="demo-badge">Ambiente demonstrativo</span><h2>Acesse sua conta</h2><p>Bem-vindo à gestão de faturas.</p>
        <label>Matrícula<span className="access-input"><UserRound size={17} aria-hidden="true" /><input aria-label="Matrícula" required value={matricula} onChange={e=>setMatricula(e.target.value)} placeholder="Digite sua matrícula" autoComplete="username" /></span></label>
        <label>Senha<span className="access-input"><LockKeyhole size={17} aria-hidden="true" /><input aria-label="Senha" required value={senha} onChange={e=>setSenha(e.target.value)} placeholder="Digite sua senha" type="password" autoComplete="current-password" /></span></label>
        <label>2º fator<span className="access-input"><Smartphone size={17} aria-hidden="true" /><input aria-label="2º fator" required value={fator} onChange={e=>setFator(e.target.value)} placeholder="Digite o código DEMO" type="password" autoComplete="off" /></span></label>
        <p className="hint"><LockKeyhole size={14} /> Acesso exclusivamente DEMO. Use as credenciais locais de demonstração. O código DEMO não é um segundo fator institucional.</p>
        {(error || auth.error) && <p className="notice error" role="alert">{error || auth.error}</p>}
        <details><summary>Perfis de demonstração</summary><p>Maker Recife: DEMO-maker<br />Maker Paulista: DEMO-maker-paulista<br />Maker Multi-Prefixo: DEMO-maker-multi<br />Checker: DEMO-checker<br />Alçada reduzida: DEMO-limite-baixo</p></details>
        <button className="primary" disabled={busy}>{busy ? "Entrando…" : "Entrar"} <ArrowRight size={17} /></button>
      </form></section>
    </div>
  </div>;
}
