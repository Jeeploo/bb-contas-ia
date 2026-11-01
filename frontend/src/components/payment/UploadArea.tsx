import { useRef, useState } from "react";
import { FileText } from "lucide-react";
export function UploadArea({
  file,
  onChange,
}: {
  file?: File;
  onChange: (file?: File) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState("");
  function select(f?: File) {
    setError("");
    if (f && !/\.(pdf|jpe?g|png)$/i.test(f.name)) {
      setError("Selecione um arquivo PDF, JPG, JPEG ou PNG.");
      return;
    }
    onChange(f);
  }
  return (
    <>
      <div
        className="upload-area"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          select(e.dataTransfer.files[0]);
        }}
      >
        <div className="pdf-icon"><FileText size={44} /><span>PDF</span></div>
        <h2>Arraste e solte os arquivos aqui</h2>
        <p>ou clique para selecionar</p>
        <small className="file-formats">Formatos aceitos: PDF, JPG, JPEG, PNG</small>
        <button className="primary" onClick={() => input.current?.click()}>
          Selecionar arquivo
        </button>
        <input
          ref={input}
          hidden
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(e) => {
            select(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        <small>
          Leitura inteligente de PDF e imagens.
        </small>
      </div>
      {error && (
        <p role="alert" className="notice error">
          {error}
        </p>
      )}
      {file && (
        <div className="file-row">
          <FileText />
          <div>
            <strong>{file.name}</strong>
            <small>
              {(file.size / 1024).toLocaleString("pt-BR", {
                maximumFractionDigits: 1,
              })}{" "}
              KB
            </small>
          </div>
          <button onClick={() => onChange(undefined)}>Remover</button>
        </div>
      )}
    </>
  );
}
