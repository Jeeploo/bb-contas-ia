import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import { useAuth } from "./auth/AuthContext";
import { AppShell } from "./components/payment/AppShell";
import { DemoAccess } from "./pages/DemoAccess";
import { PaymentJourney } from "./pages/PaymentJourney";
import { InvoiceHistory } from "./pages/InvoiceHistory";
import "./styles.css";
import "./visual.css";
function App() {
  const { session, loading } = useAuth();
  if (loading) return <p role="status">Conferindo sessão…</p>;
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={session ? <Navigate to="/pagamentos" replace /> : <DemoAccess />}
        />
        <Route element={session ? <AppShell /> : <Navigate to="/" replace />}>
          <Route path="pagamentos" element={<PaymentJourney />} />
          <Route path="faturas" element={<InvoiceHistory />} />
          <Route
            path="relatorios"
            element={
              <>
                <div className="page-title"><h1>Relatórios</h1><p>Acompanhe as informações das suas faturas.</p></div>
                <section className="card">
                  <h2>Em breve</h2>
                  <p>
                    Os relatórios serão disponibilizados em uma próxima etapa do
                    MVP.
                  </p>
                </section>
              </>
            }
          />
        </Route>
        <Route
          path="*"
          element={<Navigate to={session ? "/pagamentos" : "/"} replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider><App /></AuthProvider>
  </React.StrictMode>,
);
