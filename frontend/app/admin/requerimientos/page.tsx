"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorBox, Empty, Loading } from "@/components/DataState";
import { usePolling } from "@/hooks/usePolling";
import { serviceRequestsApi } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const TABS: { code: string; label: string }[] = [
  { code: "NUEVO,ASIGNADO,EN_PROCESO", label: "Abiertos" },
  { code: "NUEVO", label: "Nuevos" },
  { code: "ASIGNADO", label: "Asignados" },
  { code: "EN_PROCESO", label: "En proceso" },
  { code: "RESUELTO", label: "Resueltos" },
  { code: "CERRADO", label: "Cerrados" },
  { code: "", label: "Todos" },
];

/** Bandeja de requerimientos de los clientes (antes solo se atendían desde el admin de Django). */
export default function StaffRequestsPage() {
  const [tab, setTab] = useState(TABS[0].code);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => setPage(1), [tab, query]);

  const { data, error, loading } = usePolling(
    () => serviceRequestsApi.list({ status: tab, q: query, page }),
    10000,
    [tab, query, page],
  );
  const { data: summary } = usePolling(() => serviceRequestsApi.summary(), 10000);

  function countFor(code: string): number | null {
    if (!summary) return null;
    if (!code) return summary.total;
    const codes = code.split(",");
    return summary.by_status.filter((s) => codes.includes(s.code)).reduce((acc, s) => acc + s.count, 0);
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Requerimientos de clientes</h1>
          <p>Solicitudes, quejas y sugerencias enviadas desde Mi Portal. Cada respuesta le llega al cliente por correo.</p>
        </div>
      </div>

      <div className="card">
        <div className="card-title" style={{ flexWrap: "wrap" }}>
          <div className="chip-row" role="tablist" aria-label="Estado">
            {TABS.map((t) => (
              <button
                key={t.label}
                type="button"
                role="tab"
                aria-selected={tab === t.code}
                className={`badge ${tab === t.code ? "on" : ""}`}
                onClick={() => setTab(t.code)}
              >
                {t.label}
                {countFor(t.code) !== null && <span className="count-pill">{countFor(t.code)}</span>}
              </button>
            ))}
          </div>
          <form
            className="row"
            onSubmit={(e) => {
              e.preventDefault();
              setQuery(search.trim());
            }}
          >
            <input
              type="search"
              placeholder="Buscar por #, asunto, cliente, NIT o contrato"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: 320 }}
              aria-label="Buscar requerimientos"
            />
            <button type="submit" className="btn-secondary">
              Buscar
            </button>
          </form>
        </div>

        <ErrorBox message={error} />
        {loading && !data && <Loading label="Cargando requerimientos…" />}
        {data && data.results.length === 0 && (
          <Empty>{query ? `No hay requerimientos que coincidan con «${query}».` : "No hay requerimientos en este estado."}</Empty>
        )}
        {data && data.results.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Asunto</th>
                  <th>Cliente</th>
                  <th>Contrato</th>
                  <th>Asesor</th>
                  <th>Estado</th>
                  <th>Creado</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.results.map((r) => (
                  <tr key={r.id}>
                    <td className="mono">#{r.id}</td>
                    <td>
                      <div>{r.subject}</div>
                      <div className="small muted">
                        {r.service} · {r.subcategory}
                        {r.message_count > 0 && ` · 💬 ${r.message_count}`}
                        {r.attachment_count > 0 && ` · 📎 ${r.attachment_count}`}
                      </div>
                    </td>
                    <td>
                      <div>{r.client_name}</div>
                      <div className="small muted">{r.client_identification}</div>
                    </td>
                    <td className="mono nowrap">{r.contract_number}</td>
                    <td>{r.assigned_to || <span className="muted">Por asignar</span>}</td>
                    <td>
                      <span className={`rq-status rq-${r.status}`}>{r.status_display}</span>
                    </td>
                    <td className="nowrap">{formatDateTime(r.created_at)}</td>
                    <td className="right">
                      <Link href={`/admin/requerimientos/${r.id}`} className="btn btn-sm">
                        Atender
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && data.count > data.results.length && (
          <div className="pagination">
            <span>
              {data.count} requerimientos · página {page}
            </span>
            <span className="row">
              <button type="button" className="btn-secondary btn-sm" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>
                Anterior
              </button>
              <button type="button" className="btn-secondary btn-sm" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>
                Siguiente
              </button>
            </span>
          </div>
        )}
      </div>
    </main>
  );
}
