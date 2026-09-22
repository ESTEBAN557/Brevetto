import { STATUS_LABELS } from "@/lib/format";
import type { ProcessingStatus } from "@/lib/types";

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  return (
    <span className={`badge badge-${status}`}>
      <span className="dot" />
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

export function NeutralBadge({ children }: { children: React.ReactNode }) {
  return <span className="badge badge-neutral">{children}</span>;
}
