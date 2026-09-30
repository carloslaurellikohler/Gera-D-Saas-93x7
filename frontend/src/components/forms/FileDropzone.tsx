import { useRef, useState } from "react";
import {
  EXTENSIONS_BY_CHOICE,
  isExtensionAllowed,
  MAX_UPLOAD_MB,
  type InputTypeChoice,
} from "../../lib/uploadConstraints";

interface Props {
  choice: InputTypeChoice;
  file: File | null;
  onFileSelected: (file: File | null, error: string | null) => void;
}

export default function FileDropzone({ choice, file, onFileSelected }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSet = (selected: File | undefined) => {
    if (!selected) {
      onFileSelected(null, null);
      return;
    }
    if (!isExtensionAllowed(selected.name, choice)) {
      onFileSelected(
        null,
        `Formato não suportado. Aceitos para ${choice}: ${EXTENSIONS_BY_CHOICE[choice].join(", ")}.`,
      );
      return;
    }
    if (selected.size > MAX_UPLOAD_MB * 1024 * 1024) {
      onFileSelected(null, `Arquivo maior que o limite de ${MAX_UPLOAD_MB}MB.`);
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
        accept={EXTENSIONS_BY_CHOICE[choice].join(",")}
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
          <small>Formatos aceitos: {EXTENSIONS_BY_CHOICE[choice].join(", ")}</small>
        </p>
      )}
    </div>
  );
}
