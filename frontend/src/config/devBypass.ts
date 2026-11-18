// Condição única do bypass de desenvolvimento (login + fluxo de faturas sem backend).
// Ativa em dois casos:
//  1) `vite` dev com VITE_DEV_BYPASS_LOGIN=true no .env.local;
//  2) build de DEMONSTRAÇÃO ABERTA (`npm run build:demo`, arquivo .env.demo com VITE_DEMO_ABERTA=true):
//     versão estática só com dados fictícios, para mostrar o fluxo sem backend e sem login.
// Um `vite build` comum (npm run build) não define VITE_DEMO_ABERTA: o bypass nunca ativa nele.

/** Build de demonstração aberta: entra direto, sem tela de login, só com dados fictícios. */
export function isDemoAberta(): boolean {
  return import.meta.env.VITE_DEMO_ABERTA === 'true';
}

export function isDevBypass(): boolean {
  return (import.meta.env.DEV && import.meta.env.VITE_DEV_BYPASS_LOGIN === 'true') || isDemoAberta();
}

/** Atraso simulado para os estados de carregamento aparecerem. */
export const mockDelay = (ms = 800) => new Promise<void>(resolve => setTimeout(resolve, ms));
