import { useId, useMemo, useRef, useState } from 'react';

export interface SearchOption { value: string; label: string }

const normalizar = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** Campo com busca por texto (combobox). Valor '' = opção "Todos/Todas". */
export function SearchSelect({ label, todosLabel, value, options, onChange, disabled }: {
  label: string;
  todosLabel: string;
  value: string;
  options: SearchOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const id = useId();
  const listId = `${id}-lista`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [aberto, setAberto] = useState(false);
  const [texto, setTexto] = useState<string | null>(null); // null = mostrando o valor selecionado
  const [ativo, setAtivo] = useState(0);

  const selecionado = options.find((o) => o.value === value);
  const todas = useMemo(() => [{ value: '', label: todosLabel }, ...options], [options, todosLabel]);
  const filtradas = useMemo(() => {
    if (!texto) return todas;
    const q = normalizar(texto);
    return todas.filter((o) => o.value && normalizar(o.label).includes(q));
  }, [texto, todas]);

  const fechar = () => { setAberto(false); setTexto(null); };
  const escolher = (v: string) => { onChange(v); fechar(); };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!aberto) { setAberto(true); setAtivo(0); return; }
      setAtivo((i) => Math.max(0, Math.min(filtradas.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1))));
    } else if (e.key === 'Enter' && aberto) {
      e.preventDefault();
      if (filtradas[ativo]) escolher(filtradas[ativo].value);
    } else if (e.key === 'Escape' && aberto) {
      // Fecha só a lista; não deixa o ESC fechar o painel inteiro.
      e.stopPropagation();
      fechar();
    }
  };

  return (
    <label className="rf-field rf-search" htmlFor={id}>
      {label}
      <input
        ref={inputRef}
        id={id}
        type="text"
        role="combobox"
        autoComplete="off"
        aria-expanded={aberto}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={aberto && filtradas[ativo] ? `${id}-op-${ativo}` : undefined}
        placeholder={todosLabel}
        disabled={disabled}
        value={texto ?? selecionado?.label ?? ''}
        onChange={(e) => { setTexto(e.target.value); setAberto(true); setAtivo(0); }}
        onFocus={() => { setAberto(true); setAtivo(0); }}
        onBlur={fechar}
        onKeyDown={onKeyDown}
      />
      {aberto && (
        <ul id={listId} role="listbox" aria-label={label} className="rf-search__list">
          {filtradas.length ? filtradas.slice(0, 60).map((o, i) => (
            <li
              key={o.value || '__todos'}
              id={`${id}-op-${i}`}
              role="option"
              aria-selected={o.value === value}
              className={`${i === ativo ? 'is-active' : ''}${o.value === value ? ' is-selected' : ''}`}
              onMouseDown={(e) => { e.preventDefault(); escolher(o.value); }}
              onMouseEnter={() => setAtivo(i)}
            >
              {o.label}
            </li>
          )) : <li className="rf-search__empty" role="presentation">Nenhum resultado</li>}
        </ul>
      )}
    </label>
  );
}
