"use client";

import Link from "next/link";
import { useState } from "react";
import { CHANNEL_LABELS, formatConfidence, formatDateTime } from "@/lib/format";
import type { Document } from "@/lib/types";
import { Empty } from "./DataState";
import { DocumentPreviewModal } from "./DocumentPreviewModal";
import { StatusBadge } from "./StatusBadge";

export function DocumentTable({ documents, showContract = true }: { documents: Document[]; showContract?: boolean }) {
  const [preview, setPreview] = useState<Document | null>(null);

  if (!documents.length) return <Empty>No hay documentos para mostrar.</Empty>;
  return (
    <>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Radicado</th>
              <th>Archivo</th>
              <th>Canal</th>
              <th>Estado</th>
              {showContract && <th>Contrato</th>}
              <th>Tipo</th>
              <th>Confianza IA</th>
              <th>Radicado el</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td className="mono nowrap">{doc.filing_number}</td>
                <td className="truncate" style={{ maxWidth: 220 }} title={doc.original_filename}>
                  {doc.original_filename}
                </td>
                <td className="nowrap">{CHANNEL_LABELS[doc.source_channel] ?? doc.source_channel}</td>
                <td>
                  <StatusBadge status={doc.processing_status} />
                </td>
                {showContract && (
                  <td className="nowrap">
                    {doc.contract_id ? (
                      <Link href={`/admin/contracts/${doc.contract_id}`}>{doc.contract_number}</Link>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                )}
                <td className="nowrap">{doc.document_type?.name ?? <span className="muted">—</span>}</td>
                <td className="nowrap">{formatConfidence(doc.ai_confidence_score)}</td>
                <td className="nowrap">{formatDateTime(doc.created_at)}</td>
                <td className="nowrap right">
                  <span className="row" style={{ justifyContent: "flex-end", gap: "0.35rem" }}>
                    <button type="button" className="btn-ghost btn-sm" onClick={() => setPreview(doc)} title="Vista previa del documento">
                      Vista previa
                    </button>
                    {doc.needs_human_review ? (
                      <Link href={`/admin/review/${doc.id}`} className="btn btn-sm">
                        Validar
                      </Link>
                    ) : (
                      <Link href={`/admin/documents/${doc.id}`} className="btn btn-secondary btn-sm">
                        Ver
                      </Link>
                    )}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {preview && <DocumentPreviewModal document={preview} onClose={() => setPreview(null)} />}
    </>
  );
}
