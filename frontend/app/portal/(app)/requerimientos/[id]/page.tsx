"use client";

import { Icon, IconName } from "@/components/portal/Icon";
import { formatDateTime } from "@/lib/format";
import type { RequestStatus } from "@/lib/client-types";
import { useServiceRequest } from "@/components/portal/RequestContext";

const STEPS: { status: RequestStatus; label: string; icon: IconName }[] = [
  { status: "NUEVO", label: "Nuevo", icon: "fileNew" },
  { status: "ASIGNADO", label: "Asignado", icon: "user" },
  { status: "EN_PROCESO", label: "En proceso", icon: "refresh" },
  { status: "RESUELTO", label: "Resuelto", icon: "check" },
  { status: "CERRADO", label: "Cerrado", icon: "lock" },
];

const shortDate = (iso: string) =>
  new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short", timeZone: "America/Bogota" }).format(new Date(iso));

export default function RequestInfoPage() {
  const { request } = useServiceRequest();
  const currentIndex = STEPS.findIndex((s) => s.status === request.status);
  const reached = new Map(request.events.map((e) => [e.status, e.created_at]));

  return (
    <div className="req-grid">
      <section className="pcard">
        <h2 className="sec-title">Información general</h2>
        <div className="psteps">
          {STEPS.map((step, index) => (
            <div key={step.status} className={`pstep${index <= currentIndex ? " done" : ""}${index === currentIndex ? " current" : ""}`}>
              <span className="c"><Icon name={step.icon} size={18} /></span>
              <strong>{step.label}</strong>
              <span>{reached.get(step.status) ? shortDate(reached.get(step.status)!) : "—"}</span>
            </div>
          ))}
        </div>
        <dl className="dl">
          <div><dt>Estado</dt><dd><span className={`rstatus ${request.status}`}>{request.status_display}</span></dd></div>
          <div><dt>Asesor asignado</dt><dd>{request.assigned_to || "Por asignar"}</dd></div>
          <div><dt>Reportado por</dt><dd>{request.reported_by}</dd></div>
          <div><dt>Fecha de inicio</dt><dd>{formatDateTime(request.created_at)}</dd></div>
          <div><dt>Última actualización</dt><dd>{formatDateTime(request.updated_at)}</dd></div>
          <div><dt>Inmueble</dt><dd>{request.property_address} · {request.contract_number}</dd></div>
        </dl>
      </section>

      <section className="pcard">
        <h2 className="sec-title">Detalle del caso</h2>
        <dl className="dl">
          <div><dt>Tipo de caso</dt><dd><span className="tag">{request.case_type}</span></dd></div>
          <div><dt>Servicio</dt><dd><span className="tag">{request.service}</span></dd></div>
          <div><dt>Subcategoría</dt><dd><span className="tag">{request.subcategory}</span></dd></div>
          <div><dt>Asunto</dt><dd>{request.subject}</dd></div>
          <div><dt>Descripción</dt><dd>{request.description}</dd></div>
        </dl>
        {request.solution && (
          <>
            <h2 className="sec-title" style={{ marginTop: "1.25rem" }}><Icon name="check" size={20} /> Solución</h2>
            <div className="solution">
              <h4>Encargado</h4>
              <p>{request.solution}</p>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
