// Visualizador do documento enviado (PDF ou imagem) com zoom e arrastar (pan).
// Sem pdf.js no projeto: o PDF usa o visualizador nativo do navegador (<object>), em modo
// "ajustar à largura". Cada página é recortada numa "folha" própria, empilhadas com 12px.
// O zoom muda o tamanho REAL do elemento: o navegador redesenha o PDF (vetor), sem esticar bitmap.
import { useCallback, useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';
import { ExternalLink, FileText, ZoomIn, ZoomOut } from 'lucide-react';
import { apiBase } from '../../api/config';

const STEP = 0.25, MIN = 0.5, MAX = 4;
const PAD = 12;            // respiro em volta das folhas, em px
// Geometria do visualizador nativo (Chrome/Edge), em pontos PDF, medida empiricamente:
// margem lateral, margem no topo e espaço entre páginas. Escalam junto com o zoom.
const PT_SIDE = 4.5, PT_TOP = 3, PT_GAP = 10.5;
const INSET = 2;           // recorte extra (px) para esconder a borda escura do visualizador
const clamp = (z: number) => Math.min(MAX, Math.max(MIN, z));

type DocProps = { file?: File; documentId?: number; documentFormat?: string };
type PdfInfo = { pages: number; w: number; h: number };

/** URL do documento: arquivo local (blob) ou o original na API. */
export function useDocumentSource({ file, documentId, documentFormat }: DocProps) {
  const [blobUrl, setBlobUrl] = useState('');
  useEffect(() => {
    if (!file) { setBlobUrl(''); return; }
    const value = URL.createObjectURL(file);
    setBlobUrl(value);
    return () => URL.revokeObjectURL(value);
  }, [file]);
  const remoteUrl = documentId ? `${apiBase(import.meta.env.VITE_API_URL)}/documentos/${documentId}/arquivo` : '';
  const url = blobUrl || (file ? '' : remoteUrl);
  const isImage = file ? file.type.startsWith('image/') : ['png', 'jpg', 'jpeg'].includes(documentFormat ?? '');
  const name = file?.name ?? (documentId ? `Fatura_${documentId}.${documentFormat ?? 'pdf'}` : 'Documento');
  return { url, isImage, name };
}

/** Lê nº de páginas e tamanho da página (MediaBox) direto dos bytes do PDF. */
function parsePdf(buf: ArrayBuffer): PdfInfo | null {
  const text = new TextDecoder('latin1').decode(buf);
  const pages = (text.match(/\/Type\s*\/Page(?![a-zA-Z])/g) ?? []).length;
  if (!pages) return null; // páginas em streams comprimidos: usa o modo simples
  const m = text.match(/\/MediaBox\s*\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\]/);
  const w = m ? Math.abs(Number(m[3]) - Number(m[1])) : 595;
  const h = m ? Math.abs(Number(m[4]) - Number(m[2])) : 842;
  return w > 0 && h > 0 ? { pages, w, h } : { pages, w: 595, h: 842 };
}

export function DocumentViewer(props: DocProps) {
  const { url, isImage, name } = useDocumentSource(props);
  const [zoom, setZoom] = useState(1);              // 1 = ajustado à largura
  const [box, setBox] = useState({ w: 0, h: 0 });
  const [pdf, setPdf] = useState<PdfInfo | null>();  // undefined = lendo
  const [img, setImg] = useState<{ w: number; h: number }>();
  const [dragging, setDragging] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; left: number; top: number } | null>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setBox({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => { setZoom(1); setImg(undefined); }, [url]);

  // Estrutura do PDF (do arquivo local ou do original na API).
  useEffect(() => {
    setPdf(undefined);
    if (!url || isImage) return;
    let active = true;
    const bytes = props.file ? props.file.arrayBuffer() : fetch(url, { credentials: 'include' }).then(r => { if (!r.ok) throw new Error(); return r.arrayBuffer(); });
    bytes.then(b => { if (active) setPdf(parsePdf(b)); }).catch(() => { if (active) setPdf(null); });
    return () => { active = false; };
  }, [url, isImage, props.file]);

  const zoomIn = useCallback(() => setZoom(z => clamp(Math.floor(z / STEP + 1e-6) * STEP + STEP)), []);
  const zoomOut = useCallback(() => setZoom(z => clamp(Math.ceil(z / STEP - 1e-6) * STEP - STEP)), []);

  // Ctrl + rolagem = zoom; rolagem normal continua rolando o documento.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      if (e.deltaY < 0) zoomIn(); else zoomOut();
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [zoomIn, zoomOut]);

  // Arrastar com o mouse altera scrollLeft/scrollTop do container.
  useEffect(() => {
    if (!dragging) return;
    const move = (e: MouseEvent) => {
      const el = scrollRef.current, d = drag.current;
      if (!el || !d) return;
      el.scrollLeft = d.left - (e.clientX - d.x);
      el.scrollTop = d.top - (e.clientY - d.y);
    };
    const up = () => { drag.current = null; setDragging(false); };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
    return () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); };
  }, [dragging]);

  // Largura da folha: zoom 1 ocupa toda a largura disponível.
  const sheetW = Math.max(box.w - PAD * 2, 50) * zoom;
  let content = null, contentH = 0;
  if (url && isImage) {
    const h = img ? sheetW * (img.h / img.w) : sheetW * 1.414;
    contentH = h;
    content = <div className="doc-viewer-sheet" style={{ width: sheetW, height: h }}>
      <img src={url} alt={`Documento ${name}`} draggable={false} onLoad={e => { const i = e.currentTarget; if (i.naturalWidth) setImg({ w: i.naturalWidth, h: i.naturalHeight }); }} />
    </div>;
  } else if (url && pdf) {
    const z = sheetW / pdf.w;                       // escala px por ponto PDF
    const pageH = pdf.h * z;
    const objW = z * (pdf.w + 2 * PT_SIDE);
    const objH = z * (PT_TOP + pdf.pages * (pdf.h + PT_GAP)) + 40;
    const src = `${url}#toolbar=0&navpanes=0&view=FitH`;
    contentH = pdf.pages * (pageH - 2 * INSET) + (pdf.pages - 1) * PAD;
    content = Array.from({ length: pdf.pages }, (_, k) => (
      <div key={k} className="doc-viewer-sheet" style={{ width: sheetW - 2 * INSET, height: pageH - 2 * INSET }}>
        <object data={src} type="application/pdf" aria-label={`${name}, página ${k + 1} de ${pdf.pages}`} tabIndex={-1}
          style={{ left: -(z * PT_SIDE + INSET), top: -(z * (PT_TOP + k * (pdf.h + PT_GAP)) + INSET), width: objW, height: objH }} />
      </div>
    ));
  } else if (url && pdf === null) {
    // PDF que não deu para ler: uma única área com o visualizador nativo (rolagem própria).
    contentH = box.h - PAD * 2;
    content = <div className="doc-viewer-sheet" style={{ width: sheetW, height: Math.max(contentH, 200) }}>
      <object data={`${url}#toolbar=0&navpanes=0&view=FitH`} type="application/pdf" aria-label={`Documento ${name}`} style={{ inset: 0, width: '100%', height: '100%' }}>
        <p className="doc-viewer-empty"><FileText aria-hidden="true" /> Prévia indisponível. Use “Abrir documento”.</p>
      </object>
    </div>;
  }
  const pannable = sheetW + PAD * 2 > box.w + 1 || contentH + PAD * 2 > box.h + 1;
  const simpleMode = url && !isImage && pdf === null;

  function onMouseDown(e: ReactMouseEvent) {
    const el = scrollRef.current;
    if (!pannable || !el || e.button !== 0) return;
    e.preventDefault();
    drag.current = { x: e.clientX, y: e.clientY, left: el.scrollLeft, top: el.scrollTop };
    setDragging(true);
  }

  return (
    <div className="doc-viewer">
      <div className="doc-viewer-zoombar" role="toolbar" aria-label="Zoom do documento">
        <button type="button" onClick={zoomOut} disabled={zoom <= MIN} aria-label="Diminuir zoom" title="Diminuir zoom"><ZoomOut size={16} /></button>
        <span aria-live="polite">{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={zoomIn} disabled={zoom >= MAX} aria-label="Aumentar zoom" title="Aumentar zoom"><ZoomIn size={16} /></button>
      </div>
      <div ref={scrollRef} className={`doc-viewer-scroll${dragging ? ' is-dragging' : ''}`}>
        {content ? (
          <div className="doc-viewer-stack" style={{ padding: PAD, gap: PAD }}>
            {content}
            {/* Camada que recebe o arrastar (o visualizador de PDF engoliria os eventos do mouse). */}
            {!simpleMode && <div className={`doc-viewer-grab${pannable ? ' is-pannable' : ''}`} onMouseDown={onMouseDown} />}
          </div>
        ) : <p className="doc-viewer-empty"><FileText aria-hidden="true" /> {url && pdf === undefined && !isImage ? 'Carregando documento…' : 'Prévia indisponível.'}</p>}
      </div>
      <div className="doc-viewer-footer">
        <span className="doc-viewer-name" title={name}><FileText size={15} aria-hidden="true" /><span>{name}</span></span>
        {url && <a className="button doc-viewer-open" href={url} target="_blank" rel="noreferrer"><ExternalLink size={14} aria-hidden="true" /> Abrir documento</a>}
      </div>
    </div>
  );
}
