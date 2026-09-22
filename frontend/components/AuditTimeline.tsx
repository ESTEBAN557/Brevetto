import { formatDateTime } from "@/lib/format";
import type { AuditLogEntry } from "@/lib/types";
import { Empty } from "./DataState";

export function AuditTimeline({ entries, showDocument = false }: { entries: AuditLogEntry[]; showDocument?: boolean }) {
  if (!entries.length) return <Empty>Sin acciones registradas todavía.</Empty>;
  return (
    <ul className="timeline">
      {entries.map((entry) => (
        <li key={entry.id}>
          <div className="row row-between">
            <strong>{entry.action_label}</strong>
            <span className="when">{formatDateTime(entry.timestamp)}</span>
          </div>
          <div className="small muted">
            {showDocument && (
              <>
                <span className="mono">{entry.filing_number}</span> ·{" "}
              </>
            )}
            {entry.performed_by ? `Usuario: ${entry.performed_by}` : "Sistema / IA"}
            {entry.ip_address ? ` · IP ${entry.ip_address}` : ""}
          </div>
          {Object.keys(entry.details ?? {}).length > 0 && (
            <details>
              <summary className="small">Detalles</summary>
              <pre>{JSON.stringify(entry.details, null, 2)}</pre>
            </details>
          )}
        </li>
      ))}
    </ul>
  );
}
