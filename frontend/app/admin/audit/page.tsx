"use client";

import { useEffect, useState } from "react";
import { AuditTable, ImmutableBadge } from "@/components/AuditTable";
import { ErrorBox, Loading } from "@/components/DataState";
import { auditApi } from "@/lib/api";
import type { AuditActionCount, AuditLogEntry, Paginated } from "@/lib/types";

interface Filters {
  q: string;
  action: string;
  performed_by: string;
  filing_number: string;
  contract_number: string;
  ip_address: string;
  timestamp_from: string;
  timestamp_to: string;
}

const EMPTY: Filters = {
  q: "",
  action: "",
  performed_by: "",
  filing_number: "",
  contract_number: "",
  ip_address: "",
  timestamp_from: "",
  timestamp_to: "",
};

export default function AuditPage() {
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<AuditLogEntry> | null>(null);
  const [actions, setActions] = useState<AuditActionCount[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function update(patch: Partial<Filters>) {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  }

  useEffect(() => {
    const handle = window.setTimeout(async () => {
      setLoading(true);
      try {
        const [list, catalog] = await Promise.all([
          auditApi.list({ ...filters, page, ordering: "-timestamp" }),
          auditApi.actions({ ...filters, action: "" }),
        ]);
        setData(list);
        setActions(catalog);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error consultando la auditoría");
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => window.clearTimeout(handle);
  }, [filters, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.count / 25)) : 1;
  const activeCount = Object.values(filters).filter(Boolean).length;

  return (
    <main className="page" style={{ maxWidth: 1400 }}>
      <div className="page-header">
        <div>
          <h1 className="row">
            Auditoría global <ImmutableBadge />
          </h1>
          <p>
            Historial completo e inmutable de cargas, clasificaciones, validaciones, ediciones, consultas, descargas y
            alertas. Solo lectura: la base de datos rechaza cualquier modificación o borrado.
          </p>
        </div>
        {data && (
          <div className="card stat" style={{ minWidth: 160 }}>
            <span className="stat-value">{data.count}</span>
            <span className="stat-label">eventos con los filtros actuales</span>
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="row" style={{ marginBottom: "0.75rem" }}>
          <input
            placeholder="Buscar en detalles (JSON), radicado, archivo, contrato, usuario o IP…"
            value={filters.q}
            onChange={(e) => update({ q: e.target.value })}
            style={{ flex: 1, minWidth: 280 }}
          />
          {activeCount > 0 && (
            <button type="button" className="btn-ghost btn-sm" onClick={() => setFilters(EMPTY)}>
              Limpiar filtros ({activeCount})
            </button>
          )}
        </div>
        <div className="chip-row" style={{ marginBottom: "0.75rem" }}>
          <button type="button" className={`badge ${filters.action === "" ? "badge-PROCESANDO" : "badge-neutral"}`} style={{ cursor: "pointer", border: 0 }} onClick={() => update({ action: "" })}>
            Todas las acciones
          </button>
          {actions.map((a) => (
            <button
              key={a.code}
              type="button"
              className={`badge ${filters.action === a.code ? "badge-PROCESANDO" : "badge-neutral"}`}
              style={{ cursor: "pointer", border: 0 }}
              onClick={() => update({ action: filters.action === a.code ? "" : a.code })}
            >
              {a.label} · {a.count}
            </button>
          ))}
        </div>
        <div className="form-grid" style={{ gridTemplateColumns: "repeat(6, minmax(0, 1fr))" }}>
          <label className="field">
            Desde
            <input type="date" value={filters.timestamp_from} onChange={(e) => update({ timestamp_from: e.target.value })} />
          </label>
          <label className="field">
            Hasta
            <input type="date" value={filters.timestamp_to} onChange={(e) => update({ timestamp_to: e.target.value })} />
          </label>
          <label className="field">
            Usuario
            <input placeholder="username o 'system'" value={filters.performed_by} onChange={(e) => update({ performed_by: e.target.value })} />
          </label>
          <label className="field">
            Radicado
            <input placeholder="RAD-20260921-000001" value={filters.filing_number} onChange={(e) => update({ filing_number: e.target.value })} />
          </label>
          <label className="field">
            Contrato
            <input placeholder="CONT-2026-042" value={filters.contract_number} onChange={(e) => update({ contract_number: e.target.value })} />
          </label>
          <label className="field">
            Dirección IP
            <input placeholder="10.0.0.1" value={filters.ip_address} onChange={(e) => update({ ip_address: e.target.value })} />
          </label>
        </div>
      </div>

      <div className="card">
        <ErrorBox message={error} />
        {loading && !data ? <Loading /> : data && <AuditTable entries={data.results} />}
        {data && (
          <div className="pagination">
            <span>
              {data.count} evento(s) · página {page} de {totalPages}
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
