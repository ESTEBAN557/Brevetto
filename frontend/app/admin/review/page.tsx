"use client";

import Link from "next/link";
import { ErrorBox, Empty, Loading } from "@/components/DataState";
import { FilingStamp } from "@/components/FilingStamp";
import { usePolling } from "@/hooks/usePolling";
import { documentsApi } from "@/lib/api";
import { CHANNEL_LABELS, formatConfidence, formatDateTime } from "@/lib/format";

export default function ReviewInboxPage() {
  const { data, error, loading } = usePolling(() => documentsApi.pendingReview(), 5000);

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Validación humana (HITL)</h1>
          <p>Documentos cuya clasificación automática no alcanzó el 85 % de confianza o cuyo contrato es ambiguo.</p>
        </div>
      </div>
      <div className="card">
        <ErrorBox message={error} />
        {loading && !data && <Loading />}
        {data && data.results.length === 0 && <Empty>No hay documentos pendientes de validación. 🎉</Empty>}
        {data && data.results.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Radicado</th>
                  <th>Archivo</th>
                  <th>Canal</th>
                  <th>Sugerencia IA</th>
                  <th>Confianza</th>
                  <th>Motivo</th>
                  <th>Recibido</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.results.map((doc) => {
                  const ai = doc.ai_extracted_data ?? {};
                  return (
                    <tr key={doc.id}>
                      <td className="nowrap">
                        <FilingStamp value={doc.filing_number} />
                      </td>
                      <td className="truncate" style={{ maxWidth: 200 }}>
                        {doc.original_filename}
                      </td>
                      <td className="nowrap">{CHANNEL_LABELS[doc.source_channel]}</td>
                      <td>
                        {ai.error ? (
                          <span className="muted">IA no disponible</span>
                        ) : (
                          <>
                            <div>{ai.document_type ?? "—"}</div>
                            <div className="small muted">
                              {ai.contract_number ?? "contrato no detectado"}
                              {ai.client_name ? ` · ${ai.client_name}` : ""}
                            </div>
                          </>
                        )}
                      </td>
                      <td>{formatConfidence(doc.ai_confidence_score)}</td>
                      <td className="small muted">
                        {ai.error
                          ? "Sin análisis IA"
                          : (doc.ai_confidence_score ?? 0) < 0.85
                            ? "Confianza baja"
                            : "Contrato no resuelto"}
                      </td>
                      <td className="nowrap">{formatDateTime(doc.created_at)}</td>
                      <td className="right">
                        <Link href={`/admin/review/${doc.id}`} className="btn btn-sm">
                          Revisar
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
