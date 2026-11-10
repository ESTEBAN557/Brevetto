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
  const [printing, setPrinting] = useState(false);

  /** US-021: imprime el documento tal como está guardado (copia local temporal; el original no cambia). */
  async function print() {
    if (!url) return;
    setPrinting(true);
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blobUrl = URL.createObjectURL(await response.blob());
      const frame = document.createElement("iframe");
      frame.style.position = "fixed";
      frame.style.width = "0";
      frame.style.height = "0";
      frame.style.border = "0";
      frame.src = blobUrl;
      frame.onload = () => {
        frame.contentWindow?.focus();
        frame.contentWindow?.print();
        window.setTimeout(() => {
          frame.remove();
          URL.revokeObjectURL(blobUrl);
        }, 60_000);
      };
      document.body.appendChild(frame);
    } catch {
      // Si el navegador bloquea la impresión directa, se abre el documento para imprimirlo desde allí.
      window.open(url, "_blank", "noopener");
    } finally {
      setPrinting(false);
    }
  }

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
            <button type="button" className="btn-secondary btn-sm" onClick={print} disabled={printing}>
              {printing ? <span className="spinner" /> : "🖨"} Imprimir
            </button>
          )}
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
