"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorBox, Empty, Loading } from "@/components/DataState";
import { ApiError, serviceRequestsApi } from "@/lib/api";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { StaffServiceRequestDetail } from "@/lib/types";

const STATUSES: { code: string; label: string; help: string }[] = [
  { code: "NUEVO", label: "Nuevo", help: "Recién creado por el cliente." },
  { code: "ASIGNADO", label: "Asignado", help: "Tiene un asesor responsable." },
  { code: "EN_PROCESO", label: "En proceso", help: "El asesor lo está gestionando." },
  { code: "RESUELTO", label: "Resuelto", help: "Requiere registrar la solución." },
  { code: "CERRADO", label: "Cerrado", help: "Final: ya no admite cambios ni mensajes." },
];

function errorText(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return err instanceof Error ? err.message : "No fue posible completar la acción";
}

/** Atención de un requerimiento: estado, asesor, solución, conversación con el cliente y adjuntos. */
export default function StaffRequestDetailPage() {
  const params = useParams<{ id: string }>();
  const [request, setRequest] = useState<StaffServiceRequestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ status: "", assigned_to: "", solution: "", note: "" });
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await serviceRequestsApi.get(params.id);
      setRequest(data);
      setForm({ status: data.status, assigned_to: data.assigned_to, solution: data.solution, note: "" });
    } catch (err) {
      setError(errorText(err));
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error && !request) {
    return (
      <main className="page">
        <ErrorBox message={error} />
        <Link href="/admin/requerimientos">← Volver a la bandeja</Link>
      </main>
    );
  }
  if (!request) return <Loading label="Cargando requerimiento…" />;

  const closed = request.status === "CERRADO";
  const needsSolution = (form.status === "RESUELTO" || form.status === "CERRADO") && !form.solution.trim();

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!request) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const body: Record<string, string> = {};
      if (form.status !== request.status) body.status = form.status;
      if (form.assigned_to.trim() !== request.assigned_to) body.assigned_to = form.assigned_to;
      if (form.solution.trim() !== request.solution) body.solution = form.solution;
      if (form.note.trim()) body.note = form.note;
      if (!Object.keys(body).length) {
        setNotice("No hay cambios para guardar.");
        return;
      }
      const updated = await serviceRequestsApi.update(request.id, body);
      setRequest(updated);
      setForm({ status: updated.status, assigned_to: updated.assigned_to, solution: updated.solution, note: "" });
      setNotice("Cambios guardados. El cliente fue notificado por correo y lo verá en Mi Portal.");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  async function sendReply(e: React.FormEvent) {
    e.preventDefault();
    if (!request || !reply.trim()) return;
    setSending(true);
    setError(null);
    try {
      await serviceRequestsApi.reply(request.id, reply.trim());
      setReply("");
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSending(false);
    }
  }

  async function uploadFiles(files: FileList | null) {
    if (!request || !files?.length) return;
    setUploading(true);
    setError(null);
    try {
      await serviceRequestsApi.attach(request.id, Array.from(files));
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function openAttachment(attachmentId: number) {
    if (!request) return;
    try {
      const data = await serviceRequestsApi.attachmentUrl(request.id, attachmentId);
      window.open(data.download_url, "_blank", "noopener");
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <p className="small">
            <Link href="/admin/requerimientos">← Requerimientos</Link>
          </p>
          <h1 className="row">
            <span className="mono">#{request.id}</span> {request.subject}
            <span className={`rq-status rq-${request.status}`}>{request.status_display}</span>
          </h1>
          <p>
            {request.case_type} · {request.service} · {request.subcategory} · creado {formatDateTime(request.created_at)}
          </p>
        </div>
      </div>

      <ErrorBox message={error} />
      {notice && (
        <div className="alert alert-success" style={{ marginBottom: "1rem" }} role="status">
          {notice}
        </div>
      )}

      <div className="split">
        <div className="stack">
          <section className="card">
            <h3>Lo que reporta el cliente</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{request.description}</p>
            <dl className="suggestion">
              <dt>Cliente</dt>
              <dd>
                {request.client_name} · {request.client_identification}
              </dd>
              <dt>Contacto</dt>
              <dd>
                {request.client_email || "sin correo"}
                {request.client_phone ? ` · ${request.client_phone}` : ""}
              </dd>
              <dt>Contrato</dt>
              <dd>
                <Link href={`/admin/contracts/${request.contract_id}`} className="mono">
                  {request.contract_number}
                </Link>{" "}
                · {request.property_address}
              </dd>
            </dl>
          </section>

          <section className="card">
            <div className="card-title">
              <h3>Conversación con el cliente</h3>
              <span className="small muted">{request.messages.length} mensaje(s)</span>
            </div>
            {request.messages.length === 0 && <Empty>Aún no hay mensajes. Escriba la primera respuesta al cliente.</Empty>}
            <ul className="chat">
              {request.messages.map((m) => (
                <li key={m.id} className={m.author_type === "PERSONAL" ? "chat-staff" : "chat-client"}>
                  <div className="chat-meta">
                    <strong>{m.author_name}</strong> · {m.author_type === "PERSONAL" ? "Coltebienes" : "Cliente"} ·{" "}
                    {formatDateTime(m.created_at)}
                  </div>
                  <div className="chat-body">{m.body}</div>
                </li>
              ))}
            </ul>
            {closed ? (
              <p className="small muted">El requerimiento está cerrado: ya no admite mensajes.</p>
            ) : (
              <form onSubmit={sendReply} className="stack" style={{ marginTop: "0.75rem" }}>
                <label className="field">
                  Responder al cliente
                  <textarea
                    rows={3}
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="Escriba la respuesta. El cliente la verá en Mi Portal y recibirá un correo."
                    maxLength={3000}
                  />
                </label>
                <div className="form-actions" style={{ marginTop: 0 }}>
                  <button type="submit" disabled={sending || !reply.trim()}>
                    {sending && <span className="spinner" />} Enviar respuesta
                  </button>
                </div>
              </form>
            )}
          </section>

          <section className="card">
            <div className="card-title">
              <h3>Adjuntos</h3>
              {!closed && (
                <label className="btn btn-secondary btn-sm" style={{ cursor: "pointer" }}>
                  {uploading ? <span className="spinner" /> : "📎"} Adjuntar archivo
                  <input
                    ref={fileInput}
                    type="file"
                    multiple
                    hidden
                    onChange={(e) => void uploadFiles(e.target.files)}
                    accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx"
                  />
                </label>
              )}
            </div>
            {request.attachments.length === 0 ? (
              <Empty>Sin adjuntos.</Empty>
            ) : (
              <ul className="file-list">
                {request.attachments.map((a) => (
                  <li key={a.id}>
                    <span className="truncate">
                      {a.original_filename}{" "}
                      <span className="small muted">
                        · {a.from_client ? "del cliente" : "de Coltebienes"} · {formatBytes(a.file_size_bytes)} ·{" "}
                        {formatDateTime(a.created_at)}
                      </span>
                    </span>
                    <button type="button" className="btn-ghost btn-sm" onClick={() => void openAttachment(a.id)}>
                      Descargar
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <div className="stack">
          <section className="card">
            <h3>Gestión del caso</h3>
            {closed ? (
              <p className="muted">Este requerimiento está cerrado. La solución registrada fue: {request.solution || "—"}</p>
            ) : (
              <form onSubmit={save} className="stack">
                <label className="field">
                  Estado
                  <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                    {STATUSES.map((s) => (
                      <option key={s.code} value={s.code}>
                        {s.label} — {s.help}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  Asesor asignado
                  <input
                    value={form.assigned_to}
                    onChange={(e) => setForm({ ...form, assigned_to: e.target.value })}
                    placeholder="Nombre del asesor responsable"
                    maxLength={120}
                  />
                  <span className="hint">Al asignar un caso nuevo, pasa automáticamente a «Asignado».</span>
                </label>
                <label className="field">
                  Solución
                  <textarea
                    rows={3}
                    value={form.solution}
                    onChange={(e) => setForm({ ...form, solution: e.target.value })}
                    placeholder="Obligatoria para marcar el caso como Resuelto o Cerrado"
                    maxLength={5000}
                  />
                </label>
                <label className="field">
                  Nota de seguimiento <span className="hint">(opcional, la ve el cliente en la línea de tiempo)</span>
                  <input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} maxLength={1000} />
                </label>
                {needsSolution && (
                  <div className="alert alert-warning">Para resolver o cerrar el caso escriba primero la solución.</div>
                )}
                <div className="form-actions" style={{ marginTop: 0 }}>
                  <button type="submit" disabled={saving || needsSolution}>
                    {saving && <span className="spinner" />} Guardar cambios
                  </button>
                </div>
              </form>
            )}
          </section>

          <section className="card">
            <h3>Seguimiento</h3>
            <ol className="timeline">
              {[...request.events].reverse().map((ev) => (
                <li key={ev.id}>
                  <strong>{ev.status_display}</strong>
                  {ev.actor && <span className="small muted"> · {ev.actor}</span>}
                  <div className="when">{formatDateTime(ev.created_at)}</div>
                  {ev.note && <div className="small">{ev.note}</div>}
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </main>
  );
}
