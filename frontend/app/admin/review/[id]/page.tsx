"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ContractPicker } from "@/components/ContractPicker";
import { ErrorBox, Loading } from "@/components/DataState";
import { FilingStamp } from "@/components/FilingStamp";
import { PdfViewer } from "@/components/PdfViewer";
import { StatusBadge } from "@/components/StatusBadge";
import { documentsApi, documentTypesApi } from "@/lib/api";
import { CHANNEL_LABELS, formatBytes, formatConfidence, formatDateTime } from "@/lib/format";
import type { Contract, Document, DocumentType } from "@/lib/types";

// Tipo devuelto por Gemini -> código del catálogo (misma tabla que el backend).
const AI_TYPE_TO_CODE: Record<string, string> = {
  POLIZA: "POLIZA_CUMPLIMIENTO",
  FACTURA: "FACTURA",
  SERVICIO_PUBLICO: "SERVICIO_PUBLICO",
  CARTA_SOLICITUD: "CARTA_SOLICITUD",
  ACTA_ENTREGA: "ACTA_ENTREGA",
  OTRO: "OTRO",
};

export default function ReviewDocumentPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [doc, setDoc] = useState<Document | null>(null);
  const [types, setTypes] = useState<DocumentType[]>([]);
  const [contract, setContract] = useState<Contract | null>(null);
  const [typeId, setTypeId] = useState("");
  const [expiration, setExpiration] = useState("");
  const [documentDate, setDocumentDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<Document | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [document, catalog] = await Promise.all([documentsApi.get(params.id), documentTypesApi.list()]);
        if (cancelled) return;
        setDoc(document);
        setTypes(catalog);
        const ai = document.ai_extracted_data ?? {};
        const suggestedCode = document.document_type?.code ?? (ai.document_type ? AI_TYPE_TO_CODE[ai.document_type] : undefined);
        const suggested = catalog.find((t) => t.code === suggestedCode);
        if (suggested) setTypeId(suggested.id);
        setExpiration(document.expiration_date ?? ai.expiration_date ?? "");
        setDocumentDate(document.document_date ?? ai.document_date ?? "");
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "No fue posible cargar el documento");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  const selectedType = useMemo(() => types.find((t) => t.id === typeId), [types, typeId]);
  const ai = doc?.ai_extracted_data ?? {};
  const confidence = doc?.ai_confidence_score ?? 0;

  async function handleValidate(event: FormEvent) {
    event.preventDefault();
    if (!doc || !contract || !typeId) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await documentsApi.validate(doc.id, {
        contract_id: contract.id,
        document_type_id: typeId,
        expiration_date: expiration || null,
        document_date: documentDate || null,
      });
      setDone(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible validar el documento");
    } finally {
      setBusy(false);
    }
  }

  async function goToNext() {
    const pending = await documentsApi.pendingReview();
    const next = pending.results.find((d) => d.id !== params.id);
    router.push(next ? `/admin/review/${next.id}` : "/admin/review");
  }

  if (error && !doc) {
    return (
      <main className="page">
        <ErrorBox message={error} />
        <Link href="/admin/review">Volver a la bandeja</Link>
      </main>
    );
  }
  if (!doc) return <Loading label="Cargando documento…" />;

  return (
    <main className="page" style={{ maxWidth: 1400 }}>
      <div className="page-header">
        <div>
          <h1 className="row">
            <FilingStamp value={doc.filing_number} size="lg" /> <StatusBadge status={doc.processing_status} />
          </h1>
          <p>
            {doc.original_filename} · {formatBytes(doc.file_size_bytes)} · {CHANNEL_LABELS[doc.source_channel]} ·
            recibido {formatDateTime(doc.created_at)}
            {doc.external_sender_name ? ` · remitente: ${doc.external_sender_name}` : ""}
          </p>
        </div>
        <Link href="/admin/review" className="btn btn-secondary">
          Volver a la bandeja
        </Link>
      </div>

      <div className="split">
        <PdfViewer documentId={doc.id} mimeType={doc.mime_type} filename={doc.original_filename} />

        <div className="stack">
          <section className="card">
            <div className="card-title">
              <h3>Sugerencias de la IA</h3>
              <span className="small muted">{formatConfidence(doc.ai_confidence_score)} de confianza</span>
            </div>
            {ai.error ? (
              <div className="alert alert-warning">El análisis automático no estuvo disponible: {ai.error}</div>
            ) : (
              <>
                <div className={`confidence${confidence < 0.85 ? " low" : ""}`} style={{ marginBottom: "0.75rem" }}>
                  <div className="bar">
                    <span style={{ width: `${Math.round(confidence * 100)}%` }} />
                  </div>
                  <span className="small">{confidence < 0.85 ? "Por debajo del umbral 85 %" : "Umbral superado"}</span>
                </div>
                <dl className="suggestion">
                  <dt>Contrato</dt>
                  <dd>{ai.contract_number ?? <span className="muted">no detectado</span>}</dd>
                  <dt>Cliente</dt>
                  <dd>
                    {ai.client_name ?? <span className="muted">—</span>}
                    {ai.client_identification ? <span className="muted"> · {ai.client_identification}</span> : null}
                  </dd>
                  <dt>Tipo</dt>
                  <dd>{ai.document_type ?? <span className="muted">—</span>}</dd>
                  <dt>Fecha documento</dt>
                  <dd>{ai.document_date ?? <span className="muted">—</span>}</dd>
                  <dt>Vencimiento</dt>
                  <dd>{ai.expiration_date ?? <span className="muted">—</span>}</dd>
                  <dt>Resumen</dt>
                  <dd className="muted">{ai.extracted_text_summary || "—"}</dd>
                </dl>
              </>
            )}
          </section>

          {done ? (
            <section className="card stack">
              <div className="alert alert-success">
                Documento archivado en el expediente <strong>{done.contract_number}</strong> como{" "}
                <strong>{done.document_type?.name}</strong>. La acción quedó registrada en la auditoría.
              </div>
              <div className="row">
                <button type="button" onClick={goToNext}>
                  Siguiente pendiente
                </button>
                <Link href={`/admin/documents/${done.id}`} className="btn btn-secondary">
                  Ver documento
                </Link>
                {done.contract_id && (
                  <Link href={`/admin/contracts/${done.contract_id}`} className="btn btn-ghost">
                    Ir al expediente
                  </Link>
                )}
              </div>
            </section>
          ) : (
            <form className="card stack" onSubmit={handleValidate}>
              <h3>Confirmar clasificación</h3>
              <label className="field">
                Contrato / expediente destino
                <span className="hint">Confirme la sugerencia o busque el contrato correcto.</span>
              </label>
              <ContractPicker
                value={contract}
                onChange={setContract}
                initialQuery={ai.contract_number ?? ai.client_identification ?? ""}
                autoSelectSingleMatch
              />
              <label className="field">
                Tipo documental
                <select value={typeId} onChange={(e) => setTypeId(e.target.value)} required>
                  <option value="">Seleccione…</option>
                  {types.map((t) => (
                    <option key={t.id} value={t.id}>
                      [{t.category}] {t.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-grid">
                <label className="field">
                  Fecha del documento
                  <input type="date" value={documentDate} onChange={(e) => setDocumentDate(e.target.value)} />
                </label>
                <label className="field">
                  Fecha de vencimiento {selectedType?.requires_expiration && <span className="hint">obligatoria para este tipo</span>}
                  <input
                    type="date"
                    value={expiration}
                    onChange={(e) => setExpiration(e.target.value)}
                    required={selectedType?.requires_expiration}
                  />
                </label>
              </div>
              <ErrorBox message={error} />
              <div className="form-actions">
                <button type="submit" disabled={busy || !contract || !typeId}>
                  {busy && <span className="spinner" />} Aprobar y archivar
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
