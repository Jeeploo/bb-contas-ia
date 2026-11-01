import { apiBase } from './config';
const base = apiBase(import.meta.env.VITE_API_URL);
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
        response = await fetch(base + path, { ...options, headers, credentials: 'include' });
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
        if (response.status === 401 && typeof window !== 'undefined' && !path.startsWith('/auth/login'))
            window.dispatchEvent(new Event('bb-session-expired'));
        if (response.status >= 500) {
            throw new ApiError(response.status, 'O serviço não conseguiu concluir a operação. Tente novamente em instantes.');
        }
        const detail = data && typeof data === 'object' && 'detail' in data ? detailMessage(data.detail) : '';
        const friendly = response.status === 404 ? 'Registro não encontrado. Atualize a página e tente novamente.' : response.status === 409 && /criador|própria/i.test(detail) ? 'Autoaprovação bloqueada: escolha um aprovador diferente do criador da ordem.' : response.status === 403 ? detail || 'Operação não autorizada para este usuário.' : detail || `Não foi possível concluir a operação (HTTP ${response.status}).`;
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

export function calculationErrorMessage(error: unknown): string {
    const detail = errorMessage(error);
    const messages: [RegExp, string][] = [
        [/sem extração/i, 'Envie e processe o PDF antes de calcular.'],
        [/Competência validada/i, 'Valide a competência nos dados principais usando o formato AAAA-MM.'],
        [/Campo obrigatório não validado/i, 'Confirme ou corrija os dados principais indicados antes de calcular.'],
        [/Componente.*(não validado|ausente)/i, 'Revise a composição da fatura: confirme os itens exigidos ou processe um documento que contenha o componente ausente.'],
        [/perfil ativo vigente/i, 'Verifique o cadastro do Prefixo: deve existir um único perfil ativo para a competência validada.'],
        [/Regra.*(ausente|inativa)/i, 'A regra cadastrada para o Prefixo precisa existir e estar ativa.'],
        [/vigência/i, 'A competência validada precisa estar dentro da vigência da regra cadastrada.'],
        [/coeficiente/i, 'O coeficiente do perfil precisa estar configurado com um número maior que zero.'],
    ];
    const friendly = messages.find(([pattern]) => pattern.test(detail))?.[1];
    return friendly ? `${friendly} Detalhe retornado pelo backend: ${detail}` : detail;
}
