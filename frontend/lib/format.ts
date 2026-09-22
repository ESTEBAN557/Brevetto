// Utilidades de presentación (fechas en zona horaria de Colombia, tamaños, etiquetas).
import type { DocumentCategory, ProcessingStatus, SourceChannel } from "./types";

const TIME_ZONE = "America/Bogota";

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: TIME_ZONE,
  }).format(new Date(iso));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes && bytes !== 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatConfidence(score: number | null | undefined): string {
  if (score === null || score === undefined) return "—";
  return `${Math.round(score * 100)} %`;
}

export const STATUS_LABELS: Record<ProcessingStatus, string> = {
  RECIBIDO: "Recibido / en cola",
  PROCESANDO: "Procesando IA",
  REQUIERE_REVISION: "Requiere revisión",
  PROCESADO: "Archivado",
  FALLIDO: "Fallido",
};

export const CHANNEL_LABELS: Record<SourceChannel, string> = {
  FISICO_ESCANEADO: "Físico escaneado",
  DIGITAL_INTERNO: "Digital interno",
  PORTAL_WEB: "Portal web",
  CORREO: "Correo electrónico",
};

export const CATEGORY_LABELS: Record<DocumentCategory, string> = {
  LEGAL: "Legales y contractuales",
  POLIZA: "Pólizas y seguros",
  SERVICIOS: "Servicios públicos",
  FINANCIERO: "Facturación y pagos",
  COMUNICACION: "Comunicaciones y solicitudes",
};

export const CATEGORY_ORDER: DocumentCategory[] = ["LEGAL", "POLIZA", "FINANCIERO", "SERVICIOS", "COMUNICACION"];

export const STAGE_LABELS: Record<string, string> = {
  expired: "Vencido",
  critical: "Crítico",
  warning: "Por vencer",
};

export function stageBadgeClass(stage: string | null | undefined): string {
  if (stage === "expired") return "badge badge-FALLIDO";
  if (stage === "critical") return "badge badge-REQUIERE_REVISION";
  if (stage === "warning") return "badge badge-RECIBIDO";
  return "badge badge-neutral";
}

export function daysUntil(dateValue: string | null | undefined): number | null {
  if (!dateValue) return null;
  const target = new Date(`${dateValue.slice(0, 10)}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}
