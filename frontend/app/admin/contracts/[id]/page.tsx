"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AuditTable, ImmutableBadge } from "@/components/AuditTable";
import { DocumentPreviewModal } from "@/components/DocumentPreviewModal";
import { FilingStamp } from "@/components/FilingStamp";
import { ErrorBox, Empty, Loading } from "@/components/DataState";
import { NeutralBadge, StatusBadge } from "@/components/StatusBadge";
import { contractsApi } from "@/lib/api";
import { CATEGORY_LABELS, CATEGORY_ORDER, daysUntil, formatDate, formatDateTime } from "@/lib/format";
import type { AuditActionCount, AuditLogEntry, Contract, Document, DocumentCategory } from "@/lib/types";

type Tab = "documents" | "audit";

const AUDIT_ACTIONS: { code: string; label: string }[] = [
  { code: "", label: "Todas" },
  { code: "CARGA", label: "Cargas" },
  { code: "CLASIFICACION_IA", label: "Clasificación IA" },
  { code: "VALIDACION_HUMANA", label: "Validaciones" },
  { code: "ACTUALIZACION_METADATOS", label: "Ediciones" },
  { code: "CONSULTA_VISUAL", label: "Consultas" },
  { code: "DESCARGA", label: "Descargas" },
  { code: "ALERTA_VENCIMIENTO", label: "Alertas" },
];

export default function ContractDetailPage() {
  const params = useParams<{ id: string }>();
  const [contract, setContract] = useState<Contract | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [trail, setTrail] = useState<AuditLogEntry[]>([]);
  const [trailCount, setTrailCount] = useState(0);
  const [trailAction, setTrailAction] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("documents");
  const [category, setCategory] = useState<DocumentCategory | "">("");
  const [typeCode, setTypeCode] = useState("");
  const [preview, setPreview] = useState<Document | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);

  const loadTrail = useCallback(async (action: string) => {
    const audit = await contractsApi.auditTrail(params.id, { action });
    setTrail(audit.results);
    setTrailCount(audit.count);
  }, [params.id]);

  useEffect(() => {
    (async () => {
      try {
        const [c, firstPage] = await Promise.all([contractsApi.get(params.id), contractsApi.documents(params.id)]);
        // El expediente se pagina de 25 en 25: se traen todas las páginas para filtrar y agrupar completo.
        const all = [...firstPage.results];
        for (let page = 2, next = firstPage.next; next && page <= 40; page += 1) {
          const more = await contractsApi.documents(params.id, { page });
          all.push(...more.results);
          next = more.next;
        }
        setContract(c);
        setDocuments(all);
        await loadTrail("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar el expediente");
      }
    })();
  }, [params.id, loadTrail]);

  useEffect(() => {
    if (contract) void loadTrail(trailAction);
  }, [trailAction, contract, loadTrail]);

  const grouped = useMemo(() => {
    const map = new Map<string, Document[]>();
    for (const doc of documents) {
      const key = doc.document_type?.category ?? "SIN_TIPO";
      if (category && key !== category) continue;
      if (typeCode && doc.document_type?.code !== typeCode) continue;
      map.set(key, [...(map.get(key) ?? []), doc]);
    }
    return map;
  }, [documents, category, typeCode]);

  // US-022: tipos documentales presentes en el expediente (para el filtro por tipo).
  const typeOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const doc of documents) if (doc.document_type) map.set(doc.document_type.code, doc.document_type.name);
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1], "es"));
  }, [documents]);
  const filtering = Boolean(category || typeCode);

  const expiring = documents.filter((d) => {
    const days = daysUntil(d.expiration_date);
    return days !== null && days <= 30;
  });

  async function exportZip() {
    if (!contract) return;
    setExporting(true);
    setExportMessage(null);
    try {
      const filename = await contractsApi.exportZip(contract.id, `expediente_${contract.contract_number}.zip`);
      setExportMessage(`Expediente descargado como ${filename}. La descarga quedó registrada en la bitácora.`);
      await loadTrail(trailAction);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar el expediente");
    } finally {
      setExporting(false);
    }
  }

  if (error && !contract) {
    return (
      <main className="page">
        <ErrorBox message={error} />
      </main>
    );
  }
  if (!contract) return <Loading label="Cargando expediente…" />;

  const orderedKeys = [...CATEGORY_ORDER.filter((k) => grouped.has(k)), ...(grouped.has("SIN_TIPO") ? ["SIN_TIPO"] : [])];

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1 className="row">
            Expediente <span className="mono">{contract.contract_number}</span> <NeutralBadge>{contract.status_label}</NeutralBadge>
          </h1>
          <p>
            {contract.client_detail?.name} · {contract.client_detail?.document_type} {contract.client_detail?.identification_number} ·{" "}
            {contract.property_address}
          </p>
          <p className="small">
            Vigencia {formatDate(contract.start_date)} → {formatDate(contract.end_date)} · Prefijo S3:{" "}
            <code>{contract.digital_record?.storage_path}</code>
          </p>
        </div>
        <div className="row">
          <button type="button" className="btn-ink" onClick={exportZip} disabled={exporting || documents.length === 0} title="Descarga todos los documentos del expediente y un manifest.json con hashes SHA-256">
            {exporting ? <span className="spinner" /> : "⬇"} Descargar Expediente (.ZIP)
          </button>
          <Link href="/admin/upload" className="btn">
            ⇪ Radicar en este expediente
          </Link>
        </div>
      </div>

      <ErrorBox message={error} />
      {exportMessage && <div className="alert alert-success" style={{ marginBottom: "1rem" }}>{exportMessage}</div>}
      {expiring.length > 0 && (
        <div className="alert alert-warning" style={{ marginBottom: "1rem" }}>
          <strong>{expiring.length} documento(s)</strong> vencidos o por vencer en 30 días:{" "}
          {expiring.map((d) => `${d.document_type?.name ?? d.filing_number} (${formatDate(d.expiration_date)})`).join(", ")}
        </div>
      )}

      <div className="tabs">
        <button type="button" className={tab === "documents" ? "active" : ""} onClick={() => setTab("documents")}>
          Documentos ({documents.length})
        </button>
        <button type="button" className={tab === "audit" ? "active" : ""} onClick={() => setTab("audit")}>
          Bitácora del Expediente ({trailCount})
        </button>
      </div>

      {tab === "documents" && (
        <div className="stack">
          <div className="row">
            <label className="row small muted" htmlFor="filter-type">
              Tipo de documento:
            </label>
            <select id="filter-type" value={typeCode} onChange={(e) => setTypeCode(e.target.value)} style={{ width: 260 }}>
              <option value="">Todos los tipos</option>
              {typeOptions.map(([code, name]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>
            <label className="row small muted" htmlFor="filter-category">
              Categoría:
            </label>
            <select
              id="filter-category"
              value={category}
              onChange={(e) => setCategory(e.target.value as DocumentCategory | "")}
              style={{ width: 220 }}
            >
              <option value="">Todas</option>
              {CATEGORY_ORDER.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_LABELS[c]}
                </option>
              ))}
            </select>
            {filtering && (
              <button
                type="button"
                className="btn-ghost btn-sm"
                onClick={() => {
                  setCategory("");
                  setTypeCode("");
                }}
              >
                Quitar filtros
              </button>
            )}
          </div>
          {orderedKeys.length === 0 && (
            <div className="card">
              <Empty>
                {documents.length === 0
                  ? "Este expediente aún no tiene documentos archivados."
                  : "No hay documentos del tipo o la categoría seleccionados en este expediente."}
              </Empty>
            </div>
          )}
          {orderedKeys.map((key) => (
            <section key={key} className="card">
              <div className="card-title">
                <h3>{key === "SIN_TIPO" ? "Sin tipificar" : CATEGORY_LABELS[key as DocumentCategory]}</h3>
                <span className="small muted">{grouped.get(key)?.length} documento(s)</span>
              </div>
              <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Radicado</th>
                    <th>Tipo</th>
                    <th>Archivo</th>
                    <th>Fecha documento</th>
                    <th>Vencimiento</th>
                    <th>Estado</th>
                    <th>Radicado el</th>
                    <th className="sticky-actions" />
                  </tr>
                </thead>
                <tbody>
                  {grouped.get(key)!.map((doc) => {
                    const days = daysUntil(doc.expiration_date);
                    return (
                      <tr key={doc.id}>
                        <td className="nowrap">
                          <FilingStamp value={doc.filing_number} />
                        </td>
                        <td>{doc.document_type?.name ?? "—"}</td>
                        <td className="truncate" style={{ maxWidth: 220 }}>
                          {doc.original_filename}
                        </td>
                        <td className="nowrap">{formatDate(doc.document_date)}</td>
                        <td className="nowrap">
                          {formatDate(doc.expiration_date)}
                          {days !== null && days <= 30 && (
                            <span className={`badge ${days < 0 ? "badge-FALLIDO" : "badge-REQUIERE_REVISION"}`} style={{ marginLeft: 6 }}>
                              {days < 0 ? "vencido" : `${days} d`}
                            </span>
                          )}
                        </td>
                        <td>
                          <StatusBadge status={doc.processing_status} />
                        </td>
                        <td className="nowrap">{formatDateTime(doc.created_at)}</td>
                        <td className="right nowrap sticky-actions">
                          <button type="button" className="btn-ghost btn-sm" onClick={() => setPreview(doc)}>
                            Vista previa
                          </button>{" "}
                          <Link href={`/admin/documents/${doc.id}`} className="btn btn-secondary btn-sm">
                            Ver
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              </div>
            </section>
          ))}
        </div>
      )}

      {tab === "audit" && (
        <section className="card">
          <div className="card-title" style={{ flexWrap: "wrap", gap: "0.75rem" }}>
            <h3 className="row">
              Bitácora del Expediente <ImmutableBadge />
            </h3>
            <div className="chip-row">
              {AUDIT_ACTIONS.map((a) => (
                <button
                  key={a.code}
                  type="button"
                  className={`badge ${trailAction === a.code ? "badge-PROCESANDO" : "badge-neutral"}`}
                  style={{ cursor: "pointer", border: 0 }}
                  onClick={() => setTrailAction(a.code)}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>
          <p className="small muted">
            Quién cargó, clasificó, validó, editó, consultó o descargó cada documento del contrato. Los registros no pueden
            modificarse ni eliminarse.
          </p>
          <AuditTable entries={trail} showContract={false} />
          {trailCount > trail.length && (
            <p className="small muted" style={{ marginTop: "0.5rem" }}>
              Mostrando {trail.length} de {trailCount}.{" "}
              <Link href={`/admin/audit?contract_number=${encodeURIComponent(contract.contract_number)}`}>Ver todo en auditoría global</Link>
            </p>
          )}
        </section>
      )}

      {preview && <DocumentPreviewModal document={preview} onClose={() => setPreview(null)} />}
    </main>
  );
}

// Tipo importado para futuras ampliaciones del filtro de bitácora (conteos por acción).
export type { AuditActionCount };
