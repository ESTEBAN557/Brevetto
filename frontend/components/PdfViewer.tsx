"use client";

import { useCallback, useEffect, useState } from "react";
import { documentsApi } from "@/lib/api";
import { Loading } from "./DataState";

interface PdfViewerProps {
  documentId: string;
  mimeType: string;
  filename: string;
}

/** Visor embebido: obtiene una URL prefirmada (15 min) y la muestra sin descargar el archivo. */
export function PdfViewer({ documentId, mimeType, filename }: PdfViewerProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await documentsApi.viewUrl(documentId);
      setUrl(data.view_url);
      setExpiresAt(new Date(Date.now() + data.expires_in_seconds * 1000));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible obtener el documento");
    }
  }, [documentId]);

  useEffect(() => {
    void load();
  }, [load]);

  const isPdf = mimeType === "application/pdf";

  return (
    <div className="viewer">
      <div className="viewer-bar">
        <span className="truncate">{filename}</span>
        <span className="row">
          {expiresAt && <span>Acceso válido hasta {expiresAt.toLocaleTimeString("es-CO")}</span>}
          <button type="button" className="btn-secondary btn-sm" onClick={load}>
            Renovar acceso
          </button>
          {url && (
            <a href={url} target="_blank" rel="noreferrer" className="small">
              Abrir en pestaña
            </a>
          )}
        </span>
      </div>
      {error && <div className="alert alert-error" style={{ margin: "0.75rem" }}>{error}</div>}
      {!url && !error && <Loading label="Cargando documento…" />}
      {url && isPdf && <iframe src={`${url}#toolbar=1&view=FitH`} title={filename} />}
      {url && !isPdf && <img src={url} alt={filename} />}
    </div>
  );
}
