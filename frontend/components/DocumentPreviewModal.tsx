"use client";

import Link from "next/link";
import { useState } from "react";
import { documentsApi } from "@/lib/api";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { Document } from "@/lib/types";
import { Modal } from "./Modal";
import { PdfViewer } from "./PdfViewer";
import { StatusBadge } from "./StatusBadge";

interface DocumentPreviewModalProps {
  document: Document;
  onClose: () => void;
}

/** US-019: previsualización integrada (iframe/imagen) con fallback a descarga segura. */
export function DocumentPreviewModal({ document: doc, onClose }: DocumentPreviewModalProps) {
  const [downloading, setDownloading] = useState(false);

  async function download() {
    setDownloading(true);
    try {
      const data = await documentsApi.downloadUrl(doc.id);
      window.open(data.download_url, "_blank", "noopener");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Modal
      size="wide"
      flush
      onClose={onClose}
      title={
        <span className="row">
          <span className="mono">{doc.filing_number}</span>
          <StatusBadge status={doc.processing_status} />
          <span className="small muted">
            {doc.original_filename} · {formatBytes(doc.file_size_bytes)} · {formatDateTime(doc.created_at)}
          </span>
        </span>
      }
      footer={
        <>
          <span className="small muted" style={{ marginRight: "auto" }}>
            Si el navegador no muestra el documento, use la descarga segura (URL válida 15 minutos).
          </span>
          <button type="button" className="btn-secondary" onClick={download} disabled={downloading}>
            {downloading && <span className="spinner" />} Descargar
          </button>
          <Link href={`/admin/documents/${doc.id}`} className="btn">
            Abrir ficha completa
          </Link>
        </>
      }
    >
      <PdfViewer documentId={doc.id} mimeType={doc.mime_type} filename={doc.original_filename} />
    </Modal>
  );
}
