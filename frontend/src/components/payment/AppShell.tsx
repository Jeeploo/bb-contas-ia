import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, Settings, Search, FileText, CreditCard, BarChart3, ChevronDown } from "lucide-react";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <img src="/assets/bb-symbol.png" alt="" />
        <strong>Banco do Brasil</strong>
      </div>
      <p>Gestão</p>
      <nav aria-label="Navegação principal">
        {[
          { to: "/faturas", label: "Faturas", Icon: FileText },
          { to: "/pagamentos", label: "Pagamentos", Icon: CreditCard },
          { to: "/relatorios", label: "Relatórios", Icon: BarChart3 },
        ].map(({ to, label, Icon }) => (
          <NavLink key={to} to={to}><Icon size={18} />{label}</NavLink>
        ))}
      </nav>
    </aside>
  );
}

export function Topbar() {
  const navigate = useNavigate();
  return (
    <header className="topbar">
      <div className="topbar-banner" aria-hidden="true" />
      <div className="header-main">
        <label className="header-search">
          <Search size={18} aria-hidden="true" />
          <input
            aria-label="Pesquisar faturas"
            placeholder="Pesquisar faturas"
            onKeyDown={e => {
              if (e.key === "Enter" && e.currentTarget.value.trim()) {
                navigate("/faturas?busca=" + encodeURIComponent(e.currentTarget.value));
              }
            }}
          />
        </label>
        <div className="greeting">
          <strong>Olá, Marcos!</strong>
          <span>Veja um resumo das atividades da sua agência.</span>
        </div>
      </div>
      <div className="header-tools">
        <span className="header-icon" role="img" aria-label="Notificações demonstrativas" title="Notificações demonstrativas"><Bell size={22} /></span>
        <span className="header-icon" role="img" aria-label="Configurações demonstrativas" title="Configurações demonstrativas"><Settings size={22} /></span>
        <div className="profile">
          <img className="avatar" src="/assets/avatar-demo.png" alt="Perfil demonstrativo de Marcos" />
          <div className="profile-details"><strong>Marcos Gomes</strong><small>Gerente de Serviços</small><small>Pref. 9090</small></div>
          <ChevronDown className="profile-chevron" size={15} aria-hidden="true" />
        </div>
      </div>
    </header>
  );
}

export function AppShell() {
  return <div className="app-shell"><Sidebar /><div className="workspace"><Topbar /><main><Outlet /></main></div></div>;
}
