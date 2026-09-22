"use client";

import Link from "next/link";
import { useState } from "react";
import { usePolling } from "@/hooks/usePolling";
import { documentsApi } from "@/lib/api";
import { STAGE_LABELS, formatDate, stageBadgeClass } from "@/lib/format";
import { ErrorBox, Loading } from "./DataState";

const WINDOWS = [7, 30, 60, 90];

/** Tarjeta "Documentos próximos a vencer" (Requerimiento Coltebienes #6). */
export function ExpiringPanel() {
  const [days, setDays] = useState(30);
  const { data, error, loading } = usePolling(() => documentsApi.expiring({ days, limit: 8 }), 60_000, [days]);

  return (
    <section className="card">
      <div className="card-title">
        <h2 className="row">
          Documentos próximos a vencer
          {data && data.count > 0 && (
            <span className={data.expired > 0 ? "badge badge-FALLIDO" : "badge badge-REQUIERE_REVISION"}>
              <span className="dot" /> {data.count}
            </span>
          )}
        </h2>
        <div className="row">
          <span className="small muted">Ventana:</span>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ width: 120 }}>
            {WINDOWS.map((w) => (
              <option key={w} value={w}>
                {w} días
              </option>
            ))}
          </select>
        </div>
      </div>
      <ErrorBox message={error} />
      {loading && !data && <Loading />}
      {data && data.count === 0 && (
        <p className="muted">No hay pólizas ni certificados vencidos o por vencer en los próximos {days} días.</p>
      )}
      {data && data.count > 0 && (
        <>
          <p className="small muted">
            {data.expired} vencido(s) · {data.expiring_soon} por vencer · corte {formatDate(data.as_of)}. Contacte al inquilino
            para gestionar la renovación.
          </p>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Estado</th>
                  <th>Documento</th>
                  <th>Contrato / inquilino</th>
                  <th>Contacto</th>
                  <th>Vence</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.results.map((doc) => {
                  const days_left = doc.days_to_expiration ?? 0;
                  return (
                    <tr key={doc.id}>
                      <td>
                        <span className={stageBadgeClass(doc.expiration_stage)}>
                          <span className="dot" />
                          {STAGE_LABELS[doc.expiration_stage ?? ""] ?? "—"}
                        </span>
                      </td>
                      <td>
                        <div>{doc.document_type?.name ?? "Sin tipificar"}</div>
                        <div className="small mono muted">{doc.filing_number}</div>
                      </td>
                      <td>
                        {doc.contract_id ? (
                          <Link href={`/admin/contracts/${doc.contract_id}`}>{doc.contract_number}</Link>
                        ) : (
                          <span className="muted">sin contrato</span>
                        )}
                        <div className="small muted">{doc.client_name ?? "—"}</div>
                      </td>
                      <td className="small">
                        {doc.client_email ? <a href={`mailto:${doc.client_email}`}>{doc.client_email}</a> : <span className="muted">—</span>}
                        {doc.client_phone && <div className="muted">{doc.client_phone}</div>}
                      </td>
                      <td className="nowrap">
                        {formatDate(doc.expiration_date)}
                        <div className={`small ${days_left < 0 ? "muted" : ""}`}>
                          {days_left < 0 ? `hace ${Math.abs(days_left)} d` : days_left === 0 ? "hoy" : `en ${days_left} d`}
                        </div>
                      </td>
                      <td className="right">
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
          {data.count > data.results.length && (
            <p className="small muted" style={{ marginTop: "0.5rem" }}>
              Mostrando {data.results.length} de {data.count}.{" "}
              <Link href={`/admin?expiring=${days}`}>Ver todos en la bandeja</Link>
            </p>
          )}
        </>
      )}
    </section>
  );
}
