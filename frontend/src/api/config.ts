export function apiBase(value: string | undefined): string {
  if (!value?.trim()) throw new Error('Configure VITE_API_URL com a origem do backend.');
  let url: URL;
  try { url = new URL(value.trim()); }
  catch { throw new Error('VITE_API_URL deve ser uma origem HTTP ou HTTPS válida.'); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/')
    throw new Error('VITE_API_URL deve conter somente a origem do backend, sem credenciais ou caminho.');
  return url.origin + '/api/v1';
}
