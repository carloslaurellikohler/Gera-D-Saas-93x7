import { useRef, useState } from "react";

interface Props {
  extensions: string[];
  maxUploadMb: number;
  file: File | null;
  onFileSelected: (file: File | null, error: string | null) => void;
}

export default function FileDropzone({ extensions, maxUploadMb, file, onFileSelected }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSet = (selected: File | undefined) => {
    if (!selected) {
      onFileSelected(null, null);
      return;
    }
    const lowerName = selected.name.toLowerCase();
    if (!extensions.some((ext) => lowerName.endsWith(ext))) {
      onFileSelected(null, `Formato não suportado. Aceitos: ${extensions.join(", ")}.`);
      return;
    }
    if (selected.size > maxUploadMb * 1024 * 1024) {
      onFileSelected(null, `Arquivo maior que o limite de ${maxUploadMb}MB.`);
      return;
    }
    onFileSelected(selected, null);
  };

  return (
    <div
      className={`dropzone${dragging ? " dragging" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        validateAndSet(e.dataTransfer.files[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={extensions.join(",")}
        style={{ display: "none" }}
        onChange={(e) => validateAndSet(e.target.files?.[0])}
      />
      {file ? (
        <p>
          <strong>{file.name}</strong> ({(file.size / 1024 / 1024).toFixed(1)}MB)
        </p>
      ) : (
        <p>
          Arraste seu arquivo aqui ou clique para selecionar
          <br />
          <small>Formatos aceitos: {extensions.join(", ")}</small>
        </p>
      )}
    </div>
  );
}
