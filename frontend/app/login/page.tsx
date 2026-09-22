"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ApiError, login } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) router.replace("/admin");
  }, [router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
      router.replace("/admin");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Usuario o contraseña incorrectos."
          : "No fue posible iniciar sesión. Verifique la conexión con el servidor.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="landing">
      <div className="card" style={{ maxWidth: 440 }}>
        <div className="brand-lockup">
          <div className="brand-chip">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
          </div>
          <div>
            <div className="kicker">Brevetto · Portal administrativo</div>
            <h1 style={{ margin: 0 }}>Ingreso</h1>
          </div>
        </div>
        <p className="muted">Personal de Coltebienes S.A. Sus acciones quedan registradas en la bitácora inmutable.</p>
        <form onSubmit={handleSubmit} className="stack">
          <label className="field">
            Usuario
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </label>
          <label className="field">
            Contraseña
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && <div className="alert alert-error">{error}</div>}
          <button type="submit" disabled={busy}>
            {busy ? <span className="spinner" /> : null} Iniciar sesión
          </button>
        </form>
      </div>
    </main>
  );
}
