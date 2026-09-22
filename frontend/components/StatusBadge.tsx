import { STATUS_LABELS } from "@/lib/format";
import type { ProcessingStatus } from "@/lib/types";

const ICONS: Record<ProcessingStatus, string> = {
  RECIBIDO: "",
  PROCESANDO: "",
  REQUIERE_REVISION: "⚑",
  PROCESADO: "✓",
  FALLIDO: "✕",
};

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  const icon = ICONS[status];
  return (
    <span className={`badge badge-${status}`}>
      {icon ? <span aria-hidden>{icon}</span> : <span className="dot" />}
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

export function NeutralBadge({ children }: { children: React.ReactNode }) {
  return <span className="badge badge-neutral">{children}</span>;
}
