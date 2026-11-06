"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AuthLayout, AuthLinks } from "@/components/portal/AuthLayout";
import { ApiError, login } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";

/** Personal de Coltebienes: correo (o usuario) y contraseña asignados; abre el portal administrativo. */
export default function StaffLoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) router.replace("/admin");
  }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(identifier.trim(), password);
      router.replace("/admin");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Usuario o contraseña incorrectos."
          : "No fue posible iniciar sesión. Verifique la conexión con el servidor.",
      );
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <p className="auth-help">
        <strong>Zona de empleados,</strong> inicia sesión con el usuario y contraseña asignados por tu líder. Tus
        acciones quedan registradas en la bitácora inmutable.
      </p>
      <form onSubmit={submit} className="auth-box" style={{ gap: "1.1rem" }}>
        <label className="ofield noicon">
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="Email o usuario"
            autoComplete="username"
            required
          />
        </label>
        <label className="ofield noicon">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Contraseña"
            autoComplete="current-password"
            required
          />
        </label>
        {error && <div className="alert alert-error">{error}</div>}
        <button type="submit" className="btn-block" disabled={busy}>
          {busy && <span className="spinner" />} Continuar
        </button>
        <AuthLinks current="staff" />
      </form>
    </AuthLayout>
  );
}
