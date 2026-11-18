// Bypass de login SOMENTE para desenvolvimento local (backend fora do ar).
// Só ativa com `vite` em modo dev E VITE_DEV_BYPASS_LOGIN=true (.env.local).
// Em `vite build`, import.meta.env.DEV é false e todo este código vira no-op.
import type { AuthSession } from '../types';
import { isDevBypass } from '../config/devBypass';

const STORAGE_KEY = 'bb-dev-bypass-session';

export const DEV_FAKE_TOKEN = 'dev-fake-token';

export function createDevSession(): AuthSession {
  return {
    usuario: { id_usuario: 0, matricula: 'DEV', nome: 'Marcos Gomes', funcao: 'Gerente de serviços' } as AuthSession['usuario'],
    prefixos: [{ id_prefixo: 1, codigo_prefixo: '9090', nome: 'Prefixo 9090' }] as AuthSession['prefixos'],
    id_prefixo_principal: 1,
    id_prefixo_ativo: 1,
    expira_em: new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString(),
  };
}

export function loadDevSession(): AuthSession | null {
  if (!isDevBypass()) return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    // Recria a sessão a partir do usuário fictício atual, evitando dados antigos salvos.
    return raw ? createDevSession() : null;
  } catch { return null; }
}

export function saveDevSession(session: AuthSession | null) {
  if (!isDevBypass()) return;
  try {
    if (session) localStorage.setItem(STORAGE_KEY, JSON.stringify({ token: DEV_FAKE_TOKEN, session }));
    else localStorage.removeItem(STORAGE_KEY);
  } catch { /* storage indisponível: sessão fica só em memória */ }
}

// Respostas fictícias para as páginas internas mostrarem layout preenchido.
export function devMockResponse(path: string, method: string): unknown {
  const p = path.split('?')[0];
  if (method !== 'GET') throw new Error('Modo DEV: ação indisponível sem backend.');
  if (p === '/auth/sessao') return loadDevSession();
  if (p === '/auth/config') return { demo_mode: false };
  if (p === '/documentos/jornada/atual') return { documento: null, processamento: null, calculo: null };
  if (p === '/documentos/jornada/checker') return [];
  if (p === '/faturas') return [
    { id_fatura: 1, tipo: 'energia', competencia: '2026-09', prefixo: 'Prefixo 9090', valor: '1543.27', solicitado_por: 'Marcos Gomes', confirmado_por: 'Checker Demo', data_confirmacao: '2026-10-05T14:20:00Z', status: 'em_processamento' },
    { id_fatura: 2, tipo: 'agua', competencia: '2026-09', prefixo: 'Prefixo 9090', valor: '312.90', solicitado_por: 'Marcos Gomes', confirmado_por: 'Checker Demo', data_confirmacao: '2026-10-07T10:02:00Z', status: 'validada' },
    { id_fatura: 3, tipo: 'energia', competencia: '2026-10', prefixo: 'Prefixo 9090', valor: '1610.45', solicitado_por: 'Marcos Gomes', confirmado_por: 'Checker Demo', data_confirmacao: '2026-11-04T16:45:00Z', status: 'revisao_necessaria' },
  ];
  if (p === '/relatorios/resumo') return {
    valor_total: '3466.62', quantidade: 3, energia: '3153.72', agua: '312.90',
    mensal: [
      { competencia: '2026-09', valor: '1856.17', energia: '1543.27', agua: '312.90' },
      { competencia: '2026-10', valor: '1610.45', energia: '1610.45', agua: '0.00' },
    ],
    prefixos: [{ prefixo: 'Prefixo 9090', valor: '3466.62' }],
  };
  return []; // listas genéricas (listAll) ficam vazias
}
