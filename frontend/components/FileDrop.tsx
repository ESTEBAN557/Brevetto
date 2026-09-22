"use client";

import { DragEvent, useRef, useState } from "react";
import { formatBytes } from "@/lib/format";

interface FileDropProps {
  files: File[];
  onChange: (files: File[]) => void;
  multiple?: boolean;
  accept?: string;
  maxSizeBytes?: number;
}

const DEFAULT_ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";
const DEFAULT_MAX = 25 * 1024 * 1024;

export function FileDrop({ files, onChange, multiple = true, accept = DEFAULT_ACCEPT, maxSizeBytes = DEFAULT_MAX }: FileDropProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [active, setActive] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);

  function addFiles(list: FileList | null) {
    if (!list) return;
    const incoming = Array.from(list);
    const rejected = incoming.filter((f) => f.size > maxSizeBytes || !/\.(pdf|png|jpe?g)$/i.test(f.name));
    const accepted = incoming.filter((f) => !rejected.includes(f));
    setWarning(
      rejected.length ? `${rejected.length} archivo(s) omitido(s): solo PDF/PNG/JPG hasta 25 MB.` : null,
    );
    onChange(multiple ? [...files, ...accepted] : accepted.slice(0, 1));
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setActive(false);
    addFiles(event.dataTransfer.files);
  }

  function remove(index: number) {
    onChange(files.filter((_, i) => i !== index));
  }

  return (
    <div>
      <div
        className={`dropzone${active ? " active" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setActive(true);
        }}
        onDragLeave={() => setActive(false)}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      >
        <strong>Arrastre {multiple ? "los archivos" : "el archivo"} aquí</strong> o haga clic para seleccionar
        <div className="muted small">PDF, PNG o JPG · máximo 25 MB por archivo</div>
        <input
          ref={inputRef}
          type="file"
          multiple={multiple}
          accept={accept}
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>
      {warning && <div className="alert alert-warning" style={{ marginTop: "0.5rem" }}>{warning}</div>}
      {files.length > 0 && (
        <ul className="file-list">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`}>
              <span className="truncate">{file.name}</span>
              <span className="row nowrap">
                <span className="muted">{formatBytes(file.size)}</span>
                <button type="button" className="btn-ghost btn-sm" onClick={() => remove(index)}>
                  Quitar
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
