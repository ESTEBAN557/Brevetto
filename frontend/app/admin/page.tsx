"use client";

import Link from "next/link";
import { useState } from "react";
import { DocumentTable } from "@/components/DocumentTable";
import { ErrorBox, Loading } from "@/components/DataState";
import { usePolling } from "@/hooks/usePolling";
import { documentsApi } from "@/lib/api";
import { STATUS_LABELS } from "@/lib/format";
import type { Paginated, Document, ProcessingStatus } from "@/lib/types";

const STATUSES: ProcessingStatus[] = ["RECIBIDO", "PROCESANDO", "REQUIERE_REVISION", "PROCESADO", "FALLIDO"];
const ACCENT: Record<ProcessingStatus, string> = {
  RECIBIDO: "accent-info",
  PROCESANDO: "accent-info",
  REQUIERE_REVISION: "accent-warning",
  PROCESADO: "accent-success",
  FALLIDO: "accent-danger",
};
const POLL_MS = 5000;

interface InboxData {
  counts: Record<ProcessingStatus, number>;
  page: Paginated<Document>;
}

export default function InboxPage() {
  const [status, setStatus] = useState<ProcessingStatus | "">("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, error, loading, lastUpdated, refresh } = usePolling<InboxData>(
    async () => {
      const [countPages, list] = await Promise.all([
        Promise.all(STATUSES.map((s) => documentsApi.list({ processing_status: s }))),
        documentsApi.list({ processing_status: status, search, page, ordering: "-created_at" }),
      ]);
      const counts = Object.fromEntries(STATUSES.map((s, i) => [s, countPages[i].count])) as Record<
        ProcessingStatus,
        number
      >;
      return { counts, page: list };
    },
    POLL_MS,
    [status, search, page],
  );

  const totalPages = data ? Math.max(1, Math.ceil(data.page.count / 25)) : 1;

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Bandeja de ingesta</h1>
          <p>
            Estado en tiempo real de la radicación y el procesamiento con IA.
            {lastUpdated && <span className="small"> Actualizado {lastUpdated.toLocaleTimeString("es-CO")}.</span>}
          </p>
        </div>
        <div className="row">
          <button type="button" className="btn-secondary" onClick={refresh}>
            Actualizar
          </button>
          <Link href="/admin/upload" className="btn">
            Radicar documentos
          </Link>
        </div>
      </div>

      <div className="grid grid-5" style={{ marginBottom: "1.25rem" }}>
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            className="card stat"
            style={{ textAlign: "left", cursor: "pointer", borderColor: status === s ? "var(--color-primary)" : undefined }}
            onClick={() => {
              setStatus(status === s ? "" : s);
              setPage(1);
            }}
          >
            <span className={`stat ${ACCENT[s]}`}>
              <span className="stat-value">{data ? data.counts[s] : "…"}</span>
              <span className="stat-label">{STATUS_LABELS[s]}</span>
            </span>
          </button>
        ))}
      </div>

      <div className="card">
        <div className="card-title">
          <h2>Documentos radicados</h2>
          <div className="row">
            <input
              placeholder="Buscar radicado, archivo, contrato, NIT…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              style={{ width: 300 }}
            />
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value as ProcessingStatus | "");
                setPage(1);
              }}
              style={{ width: 200 }}
            >
              <option value="">Todos los estados</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </div>
        </div>
        <ErrorBox message={error} />
        {loading && !data ? <Loading /> : data && <DocumentTable documents={data.page.results} />}
        {data && (
          <div className="pagination">
            <span>
              {data.page.count} documento(s) · página {page} de {totalPages}
            </span>
            <span className="row">
              <button type="button" className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Anterior
              </button>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                Siguiente
              </button>
            </span>
          </div>
        )}
      </div>
    </main>
  );
}
