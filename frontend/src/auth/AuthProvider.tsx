import { useEffect, useState, type ReactNode } from 'react';
import { request, ApiError, errorMessage } from '../api/client';
import type { AuthSession } from '../types';
import { AuthContext } from './AuthContext';
import { isDemoAberta, isDevBypass } from '../config/devBypass';
import { createDevSession, loadDevSession, saveDevSession } from './devBypass';
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [changingPrefix, setChangingPrefix] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    // Demo aberta: já entra com o usuário fictício, sem passar pela tela de login.
    if (isDemoAberta()) { setSession(createDevSession()); setLoading(false); return () => { active = false; }; }
    if (isDevBypass()) { setSession(loadDevSession()); setLoading(false); return () => { active = false; }; }
    request<AuthSession>('/auth/sessao').then(s => { if (active) setSession(s); }).catch(e => {
      if (active && !(e instanceof ApiError && e.status === 401)) setError(errorMessage(e));
    }).finally(() => { if (active) setLoading(false); });
    const expired = () => { setSession(null); };
    window.addEventListener('bb-session-expired', expired);
    return () => { active = false; window.removeEventListener('bb-session-expired', expired); };
  }, []);
  async function login(matricula: string, senha: string, segundo_fator: string) {
    if (isDevBypass()) { const fake = createDevSession(); saveDevSession(fake); setSession(fake); setError(''); return; }
    const result = await request<AuthSession>('/auth/login', { method:'POST', body:JSON.stringify({matricula,senha,segundo_fator}) });
    setSession(result); setError('');
  }
  async function logout() {
    // Demo aberta: "Sair" não leva à tela de login; o visitante continua navegando.
    if (isDemoAberta()) return;
    if (isDevBypass()) { saveDevSession(null); setSession(null); setError(''); return; }
    try { await request('/auth/logout', { method:'POST' }); }
    catch (e) { if (!(e instanceof ApiError && e.status === 401)) throw e; }
    setSession(null); setError('');
  }
  async function selectPrefix(id: number) {
    if (isDevBypass()) { if (session) { const next = { ...session, id_prefixo_ativo: id }; saveDevSession(next); setSession(next); } return; }
    setChangingPrefix(true);
    try { setSession(await request<AuthSession>('/auth/prefixo', {method:'PATCH',body:JSON.stringify({id_prefixo:id})})); }
    finally { setChangingPrefix(false); }
  }
  return <AuthContext.Provider value={{session,loading,changingPrefix,error,login,logout,selectPrefix}}>{children}</AuthContext.Provider>;
}
