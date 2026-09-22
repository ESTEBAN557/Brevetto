"use client";

import { useState } from "react";
import { usePolling } from "@/hooks/usePolling";
import { metricsApi } from "@/lib/api";
import { CHANNEL_LABELS } from "@/lib/format";
import { ErrorBox } from "./DataState";

const PERIODS = [7, 30, 90, 365];

function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)} %`;
}

function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 90) return `${Math.round(seconds)} s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)} min`;
  return `${(seconds / 3600).toFixed(1)} h`;
}

/** KPIs ejecutivos de gestión documental (GET /api/v1/metrics/summary/). */
export function KpiCards() {
  const [days, setDays] = useState(30);
  const { data, error, loading } = usePolling(() => metricsApi.summary(days), 60_000, [days]);

  return (
    <section style={{ marginBottom: "1.25rem" }}>
      <div className="row row-between" style={{ marginBottom: "0.6rem" }}>
        <div>
          <div className="small muted" style={{ fontFamily: "var(--font-ui)", letterSpacing: "0.12em", textTransform: "uppercase", fontSize: "0.68rem" }}>
            Coltebienes S.A. · Eficiencia ganada
          </div>
          <h2 style={{ margin: 0 }}>Indicadores ejecutivos</h2>
        </div>
        <label className="row small muted">
          Periodo
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ width: 130 }}>
            {PERIODS.map((p) => (
              <option key={p} value={p}>
                {p === 365 ? "12 meses" : `${p} días`}
              </option>
            ))}
          </select>
        </label>
      </div>
      <ErrorBox message={error} />
      <div className="kpi-grid">
        <div className="card kpi kpi-success">
          <div className="kpi-value">{data ? percent(data.ai.automation_rate) : loading ? "…" : "—"}</div>
          <div className="kpi-label">Automatización IA</div>
          <div className="meter">
            <span style={{ width: `${Math.round((data?.ai.automation_rate ?? 0) * 100)}%` }} />
          </div>
          <div className="kpi-foot">
            {data ? `${data.ai.auto_classified} de ${data.ai.documents_analyzed} clasificados sin intervención` : "clasificados sin intervención humana"}
          </div>
        </div>
        <div className="card kpi kpi-info">
          <div className="kpi-value">{data ? percent(data.ai.accuracy_rate) : "…"}</div>
          <div className="kpi-label">Acierto de la IA</div>
          <div className="kpi-foot">
            {data ? `${data.ai.auto_corrected_by_staff} corrección(es) del personal · confianza media ${percent(data.ai.average_confidence)}` : ""}
          </div>
        </div>
        <div className="card kpi kpi-info">
          <div className="kpi-value">{data ? duration(data.processing.average_seconds_to_classification) : "…"}</div>
          <div className="kpi-label">Radicación → clasificación</div>
          <div className="kpi-foot">tiempo promedio del pipeline asíncrono</div>
        </div>
        <div className="card kpi kpi-success">
          <div className="kpi-value">{data ? `${data.processing.estimated_hours_saved} h` : "…"}</div>
          <div className="kpi-label">Horas ahorradas (estimado)</div>
          <div className="kpi-foot">
            {data ? `${data.processing.manual_minutes_per_document_assumption} min manuales por documento evitados` : ""}
          </div>
        </div>
        <div className={`card kpi ${data && data.documents.pending_review > 0 ? "kpi-warning" : "kpi-success"}`}>
          <div className="kpi-value">{data ? data.documents.pending_review : "…"}</div>
          <div className="kpi-label">Pendientes de validación</div>
          <div className="kpi-foot">
            {data ? `${data.documents.total} documentos · ${data.documents.filed_in_period} radicados en el periodo` : ""}
          </div>
        </div>
        <div className={`card kpi ${data && data.expirations.expired > 0 ? "kpi-danger" : data && data.expirations.total > 0 ? "kpi-warning" : "kpi-success"}`}>
          <div className="kpi-value">{data ? data.expirations.total : "…"}</div>
          <div className="kpi-label">Vencidos o por vencer</div>
          <div className="kpi-foot">
            {data ? `${data.expirations.expired} vencidos · ${data.expirations.critical_7_days} críticos · ${data.expirations.alerts_emitted} alertas emitidas` : ""}
          </div>
        </div>
      </div>
      {data && (
        <div className="row small muted" style={{ marginTop: "0.6rem" }}>
          <span>Por canal:</span>
          <span className="chip-row">
            {data.documents.by_channel.map((c) => (
              <span key={c.code} className="badge badge-neutral">
                {CHANNEL_LABELS[c.code] ?? c.label}: {c.count}
              </span>
            ))}
          </span>
          <span>· {data.contracts.active} contratos activos · {data.audit.total_events} eventos auditados</span>
        </div>
      )}
    </section>
  );
}
