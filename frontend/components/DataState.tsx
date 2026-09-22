export function Loading({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="empty">
      <span className="spinner" /> {label}
    </div>
  );
}

export function ErrorBox({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="alert alert-error">{message}</div>;
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}
