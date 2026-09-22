"use client";

import Link from "next/link";
import { useState } from "react";
import { formatDateTime } from "@/lib/format";
import type { AuditLogEntry } from "@/lib/types";
import { Empty } from "./DataState";
import { Modal } from "./Modal";

export function ImmutableBadge() {
  return (
    <span className="badge badge-immutable" title="Tabla append-only: triggers BEFORE UPDATE/DELETE en PostgreSQL 16 (migración documents.0002)">
      🔒 Registro Inmutable · PostgreSQL Trigger Protected
    </span>
  );
}

const ACTION_CLASS: Record<string, string> = {
  CARGA: "badge-RECIBIDO",
  CLASIFICACION_IA: "badge-PROCESANDO",
  VALIDACION_HUMANA: "badge-PROCESADO",
  ACTUALIZACION_METADATOS: "badge-neutral",
  CONSULTA_VISUAL: "badge-neutral",
  DESCARGA: "badge-neutral",
  ALERTA_VENCIMIENTO: "badge-REQUIERE_REVISION",
};

function summarizeDetails(details: Record<string, unknown>): string {
  const parts: string[] = [];
  const d = details as Record<string, unknown>;
  if (typeof d.reason === "string") parts.push(`motivo: ${d.reason}`);
  if (typeof d.confidence === "number") parts.push(`confianza ${Math.round(d.confidence * 100)} %`);
  if (d.auto_associated) parts.push("auto-asociado");
  if (typeof d.export_type === "string") parts.push(`exportación ${d.export_type}`);
  if (typeof d.stage === "string") parts.push(`etapa ${d.stage}`);
  if (d.changes && typeof d.changes === "object") parts.push(`campos: ${Object.keys(d.changes as object).join(", ")}`);
  if (typeof d.source === "string") parts.push(`origen ${d.source}`);
  if (!parts.length) {
    const keys = Object.keys(d);
    return keys.length ? `${keys.length} campo(s)` : "—";
  }
  return parts.join(" · ");
}

interface AuditTableProps {
  entries: AuditLogEntry[];
  showDocument?: boolean;
  showContract?: boolean;
}

/** Tabla interactiva de eventos con inspector JSON del payload `details`. */
export function AuditTable({ entries, showDocument = true, showContract = true }: AuditTableProps) {
  const [selected, setSelected] = useState<AuditLogEntry | null>(null);

  if (!entries.length) return <Empty>No hay eventos de auditoría para los criterios seleccionados.</Empty>;

  return (
    <>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Fecha y hora</th>
              <th>Acción</th>
              {showDocument && <th>Documento</th>}
              {showContract && <th>Contrato</th>}
              <th>Usuario</th>
              <th>IP</th>
              <th>Resumen</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id}>
                <td className="nowrap">{formatDateTime(entry.timestamp)}</td>
                <td>
                  <span className={`badge ${ACTION_CLASS[entry.action] ?? "badge-neutral"}`}>{entry.action_label}</span>
                </td>
                {showDocument && (
                  <td>
                    <Link href={`/admin/documents/${entry.document}`} className="mono small">
                      {entry.filing_number}
                    </Link>
                    {entry.original_filename && (
                      <div className="small muted truncate" style={{ maxWidth: 200 }}>
                        {entry.original_filename}
                      </div>
                    )}
                  </td>
                )}
                {showContract && (
                  <td className="nowrap">
                    {entry.contract_id ? (
                      <Link href={`/admin/contracts/${entry.contract_id}`}>{entry.contract_number}</Link>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                )}
                <td className="nowrap">{entry.performed_by ?? <span className="muted">Sistema / IA</span>}</td>
                <td className="mono small nowrap">{entry.ip_address ?? "—"}</td>
                <td className="small muted truncate" style={{ maxWidth: 260 }}>
                  {summarizeDetails(entry.details ?? {})}
                </td>
                <td className="right">
                  <button type="button" className="btn-secondary btn-sm" onClick={() => setSelected(entry)}>
                    Inspeccionar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <Modal
          title={
            <span className="row">
              {selected.action_label} <ImmutableBadge />
            </span>
          }
          onClose={() => setSelected(null)}
        >
          <dl className="suggestion" style={{ marginBottom: "1rem" }}>
            <dt>ID del evento</dt>
            <dd className="mono small">{selected.id}</dd>
            <dt>Fecha y hora</dt>
            <dd>{formatDateTime(selected.timestamp)}</dd>
            <dt>Documento</dt>
            <dd>
              <Link href={`/admin/documents/${selected.document}`} className="mono">
                {selected.filing_number}
              </Link>
              {selected.original_filename ? <span className="muted"> · {selected.original_filename}</span> : null}
            </dd>
            <dt>Contrato</dt>
            <dd>{selected.contract_number ?? <span className="muted">sin asociar</span>}</dd>
            <dt>Usuario</dt>
            <dd>{selected.performed_by ?? "Sistema / IA"}</dd>
            <dt>IP · agente</dt>
            <dd className="small">
              {selected.ip_address ?? "—"} · {selected.user_agent || "—"}
            </dd>
          </dl>
          <h4 className="small muted" style={{ marginBottom: "0.35rem" }}>
            Payload `details`
          </h4>
          <pre className="json-view">{JSON.stringify(selected.details ?? {}, null, 2)}</pre>
        </Modal>
      )}
    </>
  );
}
