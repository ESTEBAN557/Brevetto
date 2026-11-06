"use client";

import { DragEvent, useRef, useState } from "react";
import { formatBytes } from "@/lib/format";
import { Icon } from "./Icon";

export const ATTACHMENT_EXTENSIONS = [
  "pdf", "jpg", "jpeg", "png", "webp", "doc", "docx", "xls", "xlsx", "mp4", "mov", "avi", "webm", "mp3", "wav",
  "ogg", "m4a",
]; // fmt: skip
const MAX_BYTES = 10 * 1024 * 1024;

/** Zona de carga de adjuntos de requerimientos (hasta 10 MB por archivo). */
export function AttachmentDrop({ files, onChange }: { files: File[]; onChange: (files: File[]) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [active, setActive] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);

  function add(list: FileList | null) {
    if (!list) return;
    const incoming = Array.from(list);
    const valid = incoming.filter((f) => f.size > 0 && f.size <= MAX_BYTES && ATTACHMENT_EXTENSIONS.includes(f.name.split(".").pop()?.toLowerCase() ?? ""));
    setWarning(valid.length < incoming.length ? "Algunos archivos se omitieron: formato no permitido o superan 10 MB." : null);
    onChange([...files, ...valid].slice(0, 10));
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setActive(false);
    add(event.dataTransfer.files);
  }

  return (
    <div>
      <div
        className={`dropzone${active ? " active" : ""}`}
        style={{ textAlign: "center", borderRadius: 16 }}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setActive(true); }}
        onDragLeave={() => setActive(false)}
        onDrop={onDrop}
      >
        <div style={{ color: "var(--stamp)" }}><Icon name="upload" size={34} /></div>
        <strong style={{ color: "var(--stamp)" }}>Arrastra y suelta tus archivos</strong>
        <div className="muted small">o <u>búscalos</u> desde tu dispositivo</div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ATTACHMENT_EXTENSIONS.map((e) => `.${e}`).join(",")}
          onChange={(e) => { add(e.target.files); e.target.value = ""; }}
        />
      </div>
      <p className="muted small" style={{ margin: "0.5rem 0 0" }}>
        PDF, JPG, PNG, WEBP, DOC, DOCX, XLS, XLSX, MP4, MOV, AVI, WEBM, MP3, WAV, OGG o M4A · hasta 10 MB cada uno
      </p>
      {warning && <div className="alert alert-warning" style={{ marginTop: "0.5rem" }}>{warning}</div>}
      {files.length > 0 && (
        <ul className="file-list">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`}>
              <span className="truncate">{file.name}</span>
              <span className="row nowrap">
                <span className="muted">{formatBytes(file.size)}</span>
                <button type="button" className="btn-ghost btn-sm" onClick={() => onChange(files.filter((_, i) => i !== index))}>Quitar</button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
