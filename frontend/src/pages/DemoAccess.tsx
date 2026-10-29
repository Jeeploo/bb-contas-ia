import { useNavigate } from "react-router-dom";
import { LockKeyhole, ArrowRight, UserRound, Smartphone } from "lucide-react";
export function DemoAccess({ onEnter }: { onEnter: () => void }) {
  const navigate = useNavigate();
  return <div className="access-page">
    <header className="access-header"><img src="/assets/bb-logo.png" alt="Banco do Brasil" /><span>Gestão de contas de água e energia</span><small>Ambiente demonstrativo</small></header>
    <div className="access">
      <section className="access-intro">
        <img className="login-hero" src="/assets/login-hero.png" alt="Colaboradora em uma agência do Banco do Brasil" />
        <div className="access-message"><h1>Juntos<br />fazemos<br /><strong>mais pelo<br />amanhã.</strong></h1><p>Mais facilidade para cuidar das faturas.<br />Mais tempo para o que importa.</p></div>
      </section>
      <section className="access-form"><form className="access-card card" onSubmit={e => { e.preventDefault(); onEnter(); navigate('/pagamentos'); }}>
        
        <span className="demo-badge">Ambiente demonstrativo</span><h2>Acesse sua conta</h2><p>Bem-vindo à gestão de faturas.</p>
        <label>Matrícula<span className="access-input"><UserRound size={17} aria-hidden="true" /><input placeholder="Digite sua matrícula" autoComplete="off" /></span></label>
        <label>Senha<span className="access-input"><LockKeyhole size={17} aria-hidden="true" /><input placeholder="Digite sua senha" type="password" autoComplete="off" /></span></label>
        <label>2º fator<span className="access-input"><Smartphone size={17} aria-hidden="true" /><input placeholder="Digite o código de acesso" autoComplete="off" /></span></label>
        <p className="hint"><LockKeyhole size={14} /> Acesso demonstrativo. Os campos não são enviados nem armazenados. Não utilize credenciais reais.</p>
        <button className="primary">Entrar <ArrowRight size={17} /></button>
      </form></section>
    </div>
  </div>;
}
