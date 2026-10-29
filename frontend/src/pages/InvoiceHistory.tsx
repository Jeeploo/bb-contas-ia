import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useResource, money, date } from "../components/ui";
export function InvoiceHistory() {
  const r = useResource(api.contas);
  const [params] = useSearchParams();
  const [search, setSearch] = useState(params.get("busca") ?? "");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const rows = r.data?.filter(c => (!status || c.situacao === status) && (!type || c.categoria === type) && `${c.id_conta} ${c.categoria} ${c.competencia} ${c.numero_conta ?? ""}`.toLowerCase().includes(search.toLowerCase()));
  return (
    <>
      <div className="page-title"><h1>Faturas</h1>
      <p>Consulte suas faturas e continue o envio dos documentos.</p></div>
      <section className="card">
        <div className="filters">
          <label>Buscar fatura<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Tipo, competência ou identificador" /></label>
          <label>Status<select value={status} onChange={e => setStatus(e.target.value)}><option value="">Todos os status</option>{[...new Set(r.data?.map(c => c.situacao))].map(x => <option key={x}>{x}</option>)}</select></label>
          <label>Tipo<select value={type} onChange={e => setType(e.target.value)}><option value="">Todos os tipos</option>{[...new Set(r.data?.map(c => c.categoria))].map(x => <option key={x}>{x}</option>)}</select></label>
        </div>
        {r.loading ? (
          <p role="status">Carregando faturas…</p>
        ) : r.error ? (
          <div role="alert">
            {r.error}
            <button onClick={r.reload}>Tentar novamente</button>
          </div>
        ) : !r.data?.length ? (
          <p>Nenhuma fatura disponível.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fatura</th><th>Status</th><th>Tipo</th>
                  <th>Competência</th>
                  <th>Vencimento</th>
                  <th>Valor</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {rows?.map((c) => (
                  <tr key={c.id_conta}>
                    <td>#{c.id_conta}</td><td><span className="status-badge">{c.situacao}</span></td><td>{c.categoria}</td>
                    <td>{c.competencia}</td>
                    <td>{date(c.data_vencimento)}</td>
                    <td>{money(c.valor_original)}</td>
                    <td>
                      <Link to={"/pagamentos?conta=" + c.id_conta}>
                        Enviar fatura
                      </Link>
                    </td>
                  </tr>
                ))}
                {!rows?.length && <tr><td colSpan={7}>Nenhuma fatura encontrada para os filtros.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
