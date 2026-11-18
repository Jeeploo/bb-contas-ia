import { Link } from 'react-router-dom';
import { BarChart3, ChevronRight, Coins, Leaf } from 'lucide-react';
import './relatorios.css';

export function Relatorios() {
  return (
    <>
      {/* Mesmas classes do título de "Pagamento de faturas" (page-title + payment-title). */}
      <div className="page-title payment-title">
        <div>
          <h1><BarChart3 className="rel-title-icon" aria-hidden="true" />Relatórios</h1>
          <p>Acompanhe os gastos e o consumo de recursos da sua unidade.</p>
        </div>
      </div>

      <div className="rel-cards">
        <Link to="/relatorios/financeiros" className="rel-card rel-card--fin">
          <span className="rel-card__body">
            <Coins size={56} strokeWidth={1.6} aria-hidden="true" />
            <span className="rel-card__title">Relatórios Financeiros<br />e Operacionais</span>
          </span>
          <span className="rel-card__arrow" aria-hidden="true"><ChevronRight size={28} /></span>
        </Link>

        <Link to="/relatorios/consumo" className="rel-card rel-card--con">
          <span className="rel-card__body">
            <Leaf size={56} strokeWidth={1.6} aria-hidden="true" />
            <span className="rel-card__title">Relatórios de Consumo<br />e Sustentabilidade</span>
          </span>
          <span className="rel-card__arrow" aria-hidden="true"><ChevronRight size={28} /></span>
        </Link>
      </div>
    </>
  );
}
