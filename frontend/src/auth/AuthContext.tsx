import { createContext, useContext } from 'react';
import type { AuthSession } from '../types';
export type AuthState = {
  session: AuthSession | null;
  loading: boolean;
  changingPrefix: boolean;
  error: string;
  login: (matricula: string, senha: string, segundo_fator: string) => Promise<void>;
  logout: () => Promise<void>;
  selectPrefix: (id: number) => Promise<void>;
};
export const AuthContext = createContext<AuthState | null>(null);
export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('Contexto de sessão indisponível.');
  return auth;
}
