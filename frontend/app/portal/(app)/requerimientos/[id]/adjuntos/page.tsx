"use client";

import { useState } from "react";
import { ErrorBox } from "@/components/DataState";
import { AttachmentDrop } from "@/components/portal/AttachmentDrop";
import { Icon } from "@/components/portal/Icon";
import { PdfIcon } from "@/components/portal/ui";
import { ApiError } from "@/lib/api";
import { clientApi } from "@/lib/client-api";
import type { ServiceRequestDetail } from "@/lib/client-types";
import { formatBytes } from "@/lib/format";
import { useServiceRequest } from "@/components/portal/RequestContext";

function FileCard({ requestId, file }: { requestId: number; file: ServiceRequestDetail["attachments"][number] }) {
  const ext = file.original_filename.split(".").pop()?.toLowerCase();
  return (
    <div className="attach-file">
      {ext === "pdf" ? <PdfIcon /> : <Icon name="clip" size={24} />}
      <div>
        <div className="nm">{file.original_filename}</div>
        <small>{formatBytes(file.file_size_bytes)} · {ext?.toUpperCase()}</small>
      </div>
      <button type="button" className="icon-btn" aria-label={`Descargar ${file.original_filename}`} onClick={() => clientApi.downloadAttachment(requestId, file.id)}>
        <Icon name="download" size={18} />
      </button>
    </div>
  );
}

export default function RequestAttachmentsPage() {
  const { request, reload } = useServiceRequest();
  const [adding, setAdding] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const closed = request.status === "CERRADO";
  const mine = request.attachments.filter((a) => a.from_client);
  const others = request.attachments.filter((a) => !a.from_client);

  async function upload() {
    setBusy(true);
    setError(null);
    try {
      await clientApi.addAttachments(request.id, files);
      setFiles([]);
      setAdding(false);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No fue posible subir los archivos.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="pcard">
      <h2 className="sec-title">Adjuntos públicos</h2>
      <div className="attach-section">
        <header><span><Icon name="user" size={16} /> Adjuntos enviados por ti</span><small>{mine.length} archivo(s)</small></header>
        {mine.length === 0 ? (
          <div className="attach-empty"><Icon name="box" size={34} /><p>No has enviado adjuntos en la bitácora.</p></div>
        ) : (
          <div className="attach-files">{mine.map((f) => <FileCard key={f.id} requestId={request.id} file={f} />)}</div>
        )}
      </div>
      <div className="attach-section">
        <header><span><Icon name="clip" size={16} /> Otros adjuntos públicos</span><small>{others.length} archivo(s)</small></header>
        {others.length === 0 ? (
          <div className="attach-empty">Coltebienes no ha compartido adjuntos en este caso.</div>
        ) : (
          <div className="attach-files">{others.map((f) => <FileCard key={f.id} requestId={request.id} file={f} />)}</div>
        )}
      </div>
      {adding && (
        <div className="stack" style={{ marginBottom: "1rem" }}>
          <AttachmentDrop files={files} onChange={setFiles} />
          <ErrorBox message={error} />
          <div className="form-actions" style={{ marginTop: 0 }}>
            <button type="button" className="btn-secondary" onClick={() => { setAdding(false); setFiles([]); }}>Cancelar</button>
            <button type="button" disabled={busy || files.length === 0} onClick={upload}>
              {busy && <span className="spinner" />} Subir archivos
            </button>
          </div>
        </div>
      )}
      {!adding && (
        <div className="form-actions" style={{ marginTop: 0 }}>
          <button type="button" className="btn-secondary" disabled={closed} onClick={() => setAdding(true)} title={closed ? "El requerimiento está cerrado" : undefined}>
            <Icon name="plus" size={16} /> Agregar archivos
          </button>
        </div>
      )}
    </section>
  );
}
