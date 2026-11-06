"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { AuthLayout, AuthLinks } from "@/components/portal/AuthLayout";
import { Icon } from "@/components/portal/Icon";
import { ApiError } from "@/lib/api";
import { getClientSession } from "@/lib/client-auth";
import { clientAuthApi } from "@/lib/client-api";

/** Clientes que ya crearon su contraseña desde Mi Portal. */
export default function ClientLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (getClientSession()) router.replace("/portal");
  }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await clientAuthApi.login(email.trim(), password);
      router.replace("/portal");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? err.message
          : "No fue posible iniciar sesión. Verifica la conexión con el servidor.",
      );
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={submit} className="auth-box" style={{ gap: "1.1rem" }}>
        <label className="ofield">
          <span className="ico"><Icon name="user" /></span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Correo electrónico"
            autoComplete="username"
            required
          />
        </label>
        <label className="ofield">
          <span className="ico"><Icon name="lock" /></span>
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
          {busy && <span className="spinner" />} Iniciar sesión
        </button>
        <Link href="/login" className="btn btn-ink btn-block">
          Iniciar sesión con código
        </Link>
        <AuthLinks current="client" />
      </form>
    </AuthLayout>
  );
}
