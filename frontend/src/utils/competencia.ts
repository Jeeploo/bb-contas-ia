const canonical = /^\d{4}-(0[1-9]|1[0-2])$/;
export function formatCompetenciaDisplay(value: string): string {
  return canonical.test(value) ? `${value.slice(5)}/${value.slice(0, 4)}` : value;
}
export function parseCompetenciaDisplay(value: string): string {
  if (canonical.test(value)) return value;
  if (/^(0[1-9]|1[0-2])\/\d{4}$/.test(value)) return `${value.slice(3)}-${value.slice(0, 2)}`;
  throw new Error('Informe a competência no formato MM/AAAA.');
}
