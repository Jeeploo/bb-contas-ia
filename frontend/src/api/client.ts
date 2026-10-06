const base = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '') + '/api/v1';
export class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
}
function detailMessage(value: unknown): string {
    if (typeof value === 'string')
        return value;
    if (Array.isArray(value))
        return value.map(detailMessage).filter(Boolean).join('; ');
    if (value && typeof value === 'object' && 'msg' in value)
        return String(value.msg);
    return '';
}
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers);
    if (options.body && !(options.body instanceof FormData))
        headers.set('Content-Type', 'application/json');
    let response: Response;
    try {
        response = await fetch(base + path, { ...options, headers });
    }
    catch {
        throw new Error('Não foi possível conectar à API. Verifique se o backend está em execução.');
    }
    const raw = await response.text();
    let data: unknown;
    try {
        data = raw ? JSON.parse(raw) : undefined;
    }
    catch {
        if (response.ok)
            throw new Error('A API retornou uma resposta inválida.');
    }
    if (!response.ok) {
        const detail = data && typeof data === 'object' && 'detail' in data ? detailMessage(data.detail) : '';
        const friendly = response.status === 404 ? 'Registro não encontrado. Atualize a página e tente novamente.' : response.status === 409 && /criador|própria/i.test(detail) ? 'Autoaprovação bloqueada: escolha um aprovador diferente do criador da ordem.' : response.status === 403 ? 'Alçada insuficiente: escolha um usuário com limite financeiro adequado.' : detail || `Não foi possível concluir a operação (HTTP ${response.status}).`;
        throw new ApiError(response.status, friendly);
    }
    return data as T;
}
export async function listAll<T>(resource: string): Promise<T[]> {
    const result: T[] = [];
    const limit = 100;
    for (let offset = 0;; offset += limit) {
        const page = await request<T[]>(`/${resource}?offset=${offset}&limit=${limit}`);
        result.push(...page);
        if (page.length < limit)
            return result;
    }
}
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Ocorreu um erro inesperado.';
