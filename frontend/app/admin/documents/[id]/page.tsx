"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AuditTimeline } from "@/components/AuditTimeline";
import { ErrorBox, Loading } from "@/components/DataState";
import { PdfViewer } from "@/components/PdfViewer";
import { StatusBadge } from "@/components/StatusBadge";
import { documentsApi, documentTypesApi } from "@/lib/api";
import { CHANNEL_LABELS, formatBytes, formatConfidence, formatDate, formatDateTime } from "@/lib/format";
import type { AuditLogEntry, Document, DocumentType } from "@/lib/types";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const [doc, setDoc] = useState<Document | null>(null);
  const [types, setTypes] = useState<DocumentType[]>([]);
  const [trail, setTrail] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [form, setForm] = useState({ document_type: "", expiration_date: "", document_date: "", external_sender_name: "" });

  const load = useCallback(async () => {
    try {
      const [document, catalog, audit] = await Promise.all([
        documentsApi.get(params.id),
        documentTypesApi.list(),
        documentsApi.auditTrail(params.id),
      ]);
      setDoc(document);
      setTypes(catalog);
      setTrail(audit.results);
      setForm({
        document_type: document.document_type?.id ?? "",
        expiration_date: document.expiration_date ?? "",
        document_date: document.document_date ?? "",
        external_sender_name: document.external_sender_name ?? "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar el documento");
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveMetadata(event: FormEvent) {
    event.preventDefault();
    if (!doc) return;
    setSaving(true);
    setError(null);
    setSaved(null);
    try {
      await documentsApi.updateMetadata(doc.id, {
        document_type: form.document_type || null,
        expiration_date: form.expiration_date || null,
        document_date: form.document_date || null,
        external_sender_name: form.external_sender_name,
      });
      setSaved("Metadatos actualizados. El cambio quedó registrado con su estado anterior y nuevo.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible actualizar los metadatos");
    } finally {
      setSaving(false);
    }
  }

  async function download() {
    if (!doc) return;
    const data = await documentsApi.downloadUrl(doc.id);
    window.open(data.download_url, "_blank", "noopener");
    const audit = await documentsApi.auditTrail(doc.id);
    setTrail(audit.results);
  }

  if (error && !doc) {
    return (
      <main className="page">
        <ErrorBox message={error} />
      </main>
    );
  }
  if (!doc) return <Loading label="Cargando documento…" />;

  return (
    <main className="page" style={{ maxWidth: 1400 }}>
      <div className="page-header">
        <div>
          <h1 className="row">
            <span className="mono">{doc.filing_number}</span> <StatusBadge status={doc.processing_status} />
          </h1>
          <p>
            {doc.original_filename} · {formatBytes(doc.file_size_bytes)} · {CHANNEL_LABELS[doc.source_channel]} · radicado{" "}
            {formatDateTime(doc.created_at)} {doc.registered_by ? `por ${doc.registered_by}` : ""}
          </p>
        </div>
        <div className="row">
          {doc.needs_human_review && (
            <Link href={`/admin/review/${doc.id}`} className="btn">
              Validar ahora
            </Link>
          )}
          <button type="button" className="btn-secondary" onClick={download}>
            Descargar
          </button>
          <button type="button" className="btn-secondary" onClick={() => window.print()}>
            Imprimir
          </button>
        </div>
      </div>

      <div className="split">
        <PdfViewer documentId={doc.id} mimeType={doc.mime_type} filename={doc.original_filename} />

        <div className="stack">
          <section className="card">
            <h3>Ficha del documento</h3>
            <dl className="suggestion">
              <dt>Contrato</dt>
              <dd>
                {doc.contract_id ? (
                  <Link href={`/admin/contracts/${doc.contract_id}`}>{doc.contract_number}</Link>
                ) : (
                  <span className="muted">sin asociar</span>
                )}
                {doc.client_name ? <span className="muted"> · {doc.client_name}</span> : null}
              </dd>
              <dt>Tipo documental</dt>
              <dd>{doc.document_type?.name ?? <span className="muted">—</span>}</dd>
              <dt>Fecha documento</dt>
              <dd>{formatDate(doc.document_date)}</dd>
              <dt>Vencimiento</dt>
              <dd>{formatDate(doc.expiration_date)}</dd>
              <dt>Confianza IA</dt>
              <dd>{formatConfidence(doc.ai_confidence_score)}</dd>
              <dt>Checksum SHA-256</dt>
              <dd className="mono small" style={{ wordBreak: "break-all" }}>
                {doc.file_hash}
              </dd>
              <dt>Ruta en bucket</dt>
              <dd className="mono small" style={{ wordBreak: "break-all" }}>
                {doc.file_path}
              </dd>
            </dl>
          </section>

          <form className="card stack" onSubmit={saveMetadata}>
            <h3>Actualizar metadatos</h3>
            <label className="field">
              Tipo documental
              <select value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })}>
                <option value="">Sin tipificar</option>
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
                <input type="date" value={form.document_date} onChange={(e) => setForm({ ...form, document_date: e.target.value })} />
              </label>
              <label className="field">
                Fecha de vencimiento
                <input type="date" value={form.expiration_date} onChange={(e) => setForm({ ...form, expiration_date: e.target.value })} />
              </label>
            </div>
            <label className="field">
              Remitente externo
              <input
                value={form.external_sender_name}
                onChange={(e) => setForm({ ...form, external_sender_name: e.target.value })}
                placeholder="Nombre de quien envía el documento"
              />
            </label>
            <ErrorBox message={error} />
            {saved && <div className="alert alert-success">{saved}</div>}
            <div className="form-actions">
              <button type="submit" disabled={saving}>
                {saving && <span className="spinner" />} Guardar cambios
              </button>
            </div>
          </form>

          <section className="card">
            <div className="card-title">
              <h3>Historial de auditoría</h3>
              <span className="small muted">{trail.length} acción(es)</span>
            </div>
            <AuditTimeline entries={trail} />
          </section>
        </div>
      </div>
    </main>
  );
}
