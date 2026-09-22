"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { DocumentTable } from "@/components/DocumentTable";
import { ErrorBox, Loading } from "@/components/DataState";
import { ExpiringPanel } from "@/components/ExpiringPanel";
import { usePolling } from "@/hooks/usePolling";
import { documentsApi } from "@/lib/api";
import { CATEGORY_LABELS, CATEGORY_ORDER, CHANNEL_LABELS, STATUS_LABELS } from "@/lib/format";
import type { Paginated, Document, DocumentCategory, ProcessingStatus, SourceChannel } from "@/lib/types";

const STATUSES: ProcessingStatus[] = ["RECIBIDO", "PROCESANDO", "REQUIERE_REVISION", "PROCESADO", "FALLIDO"];
const CHANNELS: SourceChannel[] = ["FISICO_ESCANEADO", "DIGITAL_INTERNO", "PORTAL_WEB", "CORREO"];
const ACCENT: Record<ProcessingStatus, string> = {
  RECIBIDO: "accent-info",
  PROCESANDO: "accent-info",
  REQUIERE_REVISION: "accent-warning",
  PROCESADO: "accent-success",
  FALLIDO: "accent-danger",
};
const POLL_MS = 5000;

interface Filters {
  q: string;
  status: ProcessingStatus | "";
  channel: SourceChannel | "";
  category: DocumentCategory | "";
  created_from: string;
  created_to: string;
  expiration_from: string;
  expiration_to: string;
  expiring_within_days: string;
}

const EMPTY_FILTERS: Filters = {
  q: "",
  status: "",
  channel: "",
  category: "",
  created_from: "",
  created_to: "",
  expiration_from: "",
  expiration_to: "",
  expiring_within_days: "",
};

interface InboxData {
  counts: Record<ProcessingStatus, number>;
  page: Paginated<Document>;
}

export default function InboxPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Inbox />
    </Suspense>
  );
}

function Inbox() {
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<Filters>({
    ...EMPTY_FILTERS,
    expiring_within_days: searchParams.get("expiring") ?? "",
  });
  const [showAdvanced, setShowAdvanced] = useState(Boolean(searchParams.get("expiring")));
  const [page, setPage] = useState(1);

  function update(patch: Partial<Filters>) {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  }

  const activeFilterCount = Object.entries(filters).filter(([key, value]) => key !== "q" && value !== "").length;

  const { data, error, loading, lastUpdated, refresh } = usePolling<InboxData>(
    async () => {
      const [countPages, list] = await Promise.all([
        Promise.all(STATUSES.map((s) => documentsApi.list({ processing_status: s }))),
        documentsApi.list({ ...filters, page, ordering: "-created_at" }),
      ]);
      const counts = Object.fromEntries(STATUSES.map((s, i) => [s, countPages[i].count])) as Record<
        ProcessingStatus,
        number
      >;
      return { counts, page: list };
    },
    POLL_MS,
    [JSON.stringify(filters), page],
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
            style={{
              textAlign: "left",
              cursor: "pointer",
              borderColor: filters.status === s ? "var(--color-primary)" : undefined,
            }}
            onClick={() => update({ status: filters.status === s ? "" : s })}
          >
            <span className={`stat ${ACCENT[s]}`}>
              <span className="stat-value">{data ? data.counts[s] : "…"}</span>
              <span className="stat-label">{STATUS_LABELS[s]}</span>
            </span>
          </button>
        ))}
      </div>

      <div style={{ marginBottom: "1.25rem" }}>
        <ExpiringPanel />
      </div>

      <div className="card">
        <div className="card-title" style={{ alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" }}>
          <h2>Documentos radicados</h2>
          <div className="row">
            <input
              placeholder="Buscar radicado, archivo, contrato, razón social o NIT…"
              value={filters.q}
              onChange={(e) => update({ q: e.target.value })}
              style={{ width: 340 }}
            />
            <select value={filters.status} onChange={(e) => update({ status: e.target.value as ProcessingStatus | "" })} style={{ width: 190 }}>
              <option value="">Todos los estados</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
            <button type="button" className="btn-secondary btn-sm" onClick={() => setShowAdvanced(!showAdvanced)}>
              Filtros avanzados{activeFilterCount ? ` (${activeFilterCount})` : ""}
            </button>
            {(activeFilterCount > 0 || filters.q) && (
              <button type="button" className="btn-ghost btn-sm" onClick={() => setFilters(EMPTY_FILTERS)}>
                Limpiar
              </button>
            )}
          </div>
        </div>

        {showAdvanced && (
          <div className="form-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))", marginBottom: "1rem" }}>
            <label className="field">
              Canal de origen
              <select value={filters.channel} onChange={(e) => update({ channel: e.target.value as SourceChannel | "" })}>
                <option value="">Todos</option>
                {CHANNELS.map((c) => (
                  <option key={c} value={c}>
                    {CHANNEL_LABELS[c]}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Categoría documental
              <select value={filters.category} onChange={(e) => update({ category: e.target.value as DocumentCategory | "" })}>
                <option value="">Todas</option>
                {CATEGORY_ORDER.map((c) => (
                  <option key={c} value={c}>
                    {CATEGORY_LABELS[c]}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Radicado desde
              <input type="date" value={filters.created_from} onChange={(e) => update({ created_from: e.target.value })} />
            </label>
            <label className="field">
              Radicado hasta
              <input type="date" value={filters.created_to} onChange={(e) => update({ created_to: e.target.value })} />
            </label>
            <label className="field">
              Vence desde
              <input type="date" value={filters.expiration_from} onChange={(e) => update({ expiration_from: e.target.value })} />
            </label>
            <label className="field">
              Vence hasta
              <input type="date" value={filters.expiration_to} onChange={(e) => update({ expiration_to: e.target.value })} />
            </label>
            <label className="field">
              Vencimiento
              <select value={filters.expiring_within_days} onChange={(e) => update({ expiring_within_days: e.target.value })}>
                <option value="">Cualquiera</option>
                <option value="0">Vencidos u hoy</option>
                <option value="7">Vencidos o en 7 días</option>
                <option value="30">Vencidos o en 30 días</option>
                <option value="90">Vencidos o en 90 días</option>
              </select>
            </label>
          </div>
        )}

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
              <button type="button" className="btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
                Siguiente
              </button>
            </span>
          </div>
        )}
      </div>
    </main>
  );
}
