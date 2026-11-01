import { useEffect, useState, type ReactNode } from 'react';
import { request, ApiError, errorMessage } from '../api/client';
import type { AuthSession } from '../types';
import { AuthContext } from './AuthContext';
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [changingPrefix, setChangingPrefix] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    request<AuthSession>('/auth/sessao').then(s => { if (active) setSession(s); }).catch(e => {
      if (active && !(e instanceof ApiError && e.status === 401)) setError(errorMessage(e));
    }).finally(() => { if (active) setLoading(false); });
    const expired = () => { setSession(null); };
    window.addEventListener('bb-session-expired', expired);
    return () => { active = false; window.removeEventListener('bb-session-expired', expired); };
  }, []);
  async function login(matricula: string, senha: string, segundo_fator: string) {
    const result = await request<AuthSession>('/auth/login', { method:'POST', body:JSON.stringify({matricula,senha,segundo_fator}) });
    setSession(result); setError('');
  }
  async function logout() {
    try { await request('/auth/logout', { method:'POST' }); }
    catch (e) { if (!(e instanceof ApiError && e.status === 401)) throw e; }
    setSession(null); setError('');
  }
  async function selectPrefix(id: number) {
    setChangingPrefix(true);
    try { setSession(await request<AuthSession>('/auth/prefixo', {method:'PATCH',body:JSON.stringify({id_prefixo:id})})); }
    finally { setChangingPrefix(false); }
  }
  return <AuthContext.Provider value={{session,loading,changingPrefix,error,login,logout,selectPrefix}}>{children}</AuthContext.Provider>;
}
