"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { AuthLayout, AuthLinks } from "@/components/portal/AuthLayout";
import { Icon } from "@/components/portal/Icon";
import { ApiError } from "@/lib/api";
import { getClientSession } from "@/lib/client-auth";
import { clientAuthApi } from "@/lib/client-api";
import type { CodeChannel, IdentificationType, RequestCodeResponse } from "@/lib/client-types";

const DOCUMENT_TYPES: { value: IdentificationType; label: string }[] = [
  { value: "NIT", label: "NIT" },
  { value: "CC", label: "Cédula de ciudadanía" },
  { value: "CE", label: "Cédula de extranjería" },
  { value: "PASAPORTE", label: "Pasaporte" },
];

const CODE_LENGTH = 6;

/** Ingreso rápido: documento + código de un solo uso por mensaje de texto o correo. */
export default function QuickLoginPage() {
  const router = useRouter();
  const [documentType, setDocumentType] = useState<IdentificationType>("NIT");
  const [number, setNumber] = useState("");
  const [channel, setChannel] = useState<CodeChannel>("sms");
  const [sent, setSent] = useState<RequestCodeResponse | null>(null);
  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(""));
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (getClientSession()) router.replace("/portal");
    if (new URLSearchParams(window.location.search).get("expired")) {
      setNotice("Tu sesión expiró. Ingresa nuevamente para continuar.");
    }
  }, [router]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(() => setCooldown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  async function requestCode(event?: FormEvent) {
    event?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await clientAuthApi.requestCode(documentType, number.trim(), channel);
      setSent(response);
      setDigits(Array(CODE_LENGTH).fill(""));
      setCooldown(45);
      window.setTimeout(() => inputs.current[0]?.focus(), 50);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429
          ? err.message
          : "No fue posible enviar el código. Intenta nuevamente en unos minutos.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function verify(code: string) {
    setBusy(true);
    setError(null);
    try {
      const session = await clientAuthApi.verifyCode(documentType, number.trim(), code);
      router.replace(session.account.has_password ? "/portal" : "/portal?crear-clave=1");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 400 ? err.message : "No fue posible validar el código.");
      setDigits(Array(CODE_LENGTH).fill(""));
      inputs.current[0]?.focus();
      setBusy(false);
    }
  }

  function setDigit(index: number, value: string) {
    const clean = value.replace(/\D/g, "");
    if (clean.length > 1) {
      // Pegado del código completo.
      const next = clean.slice(0, CODE_LENGTH).split("");
      setDigits([...next, ...Array(CODE_LENGTH - next.length).fill("")]);
      if (next.length === CODE_LENGTH) void verify(next.join(""));
      return;
    }
    const next = [...digits];
    next[index] = clean;
    setDigits(next);
    if (clean && index < CODE_LENGTH - 1) inputs.current[index + 1]?.focus();
    if (next.every(Boolean)) void verify(next.join(""));
  }

  function onKeyDown(index: number, key: string) {
    if (key === "Backspace" && !digits[index] && index > 0) inputs.current[index - 1]?.focus();
  }

  return (
    <AuthLayout>
      {notice && <div className="alert alert-info">{notice}</div>}
      {!sent ? (
        <form onSubmit={requestCode} className="auth-box" style={{ gap: "1.1rem" }}>
          <label className="ofield">
            <span className="lab">Tipo de documento</span>
            <span className="ico"><Icon name="idCard" /></span>
            <select value={documentType} onChange={(e) => setDocumentType(e.target.value as IdentificationType)}>
              {DOCUMENT_TYPES.map((type) => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
          </label>
          <label className="ofield">
            <span className="ico"><Icon name="hash" /></span>
            <input
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              placeholder="Número de documento"
              inputMode="numeric"
              autoComplete="off"
              required
            />
          </label>
          <p className="auth-help">Selecciona el medio preferido de contacto para recibir el código de verificación.</p>
          <div className="radio-row">
            <label>
              <input type="radio" name="channel" checked={channel === "sms"} onChange={() => setChannel("sms")} />
              Mensaje de texto
            </label>
            <label>
              <input type="radio" name="channel" checked={channel === "email"} onChange={() => setChannel("email")} />
              Correo electrónico
            </label>
          </div>
          {error && <div className="alert alert-error">{error}</div>}
          <button type="submit" className="btn-block" disabled={busy || !number.trim()}>
            {busy && <span className="spinner" />} Continuar
          </button>
          <div className="auth-divider">o iniciar sesión con usuario y contraseña</div>
          <AuthLinks current="quick" />
        </form>
      ) : (
        <div className="auth-box" style={{ gap: "1.1rem" }}>
          <p className="auth-help">
            {sent.destination ? (
              <>
                Enviamos un código de 6 dígitos {sent.channel === "email" ? "al correo" : "al número"}{" "}
                <strong>{sent.destination}</strong>.
              </>
            ) : (
              sent.detail
            )}
          </p>
          <div className="otp-row">
            {digits.map((digit, index) => (
              <input
                key={index}
                ref={(el) => {
                  inputs.current[index] = el;
                }}
                value={digit}
                onChange={(e) => setDigit(index, e.target.value)}
                onKeyDown={(e) => onKeyDown(index, e.key)}
                inputMode="numeric"
                autoComplete={index === 0 ? "one-time-code" : "off"}
                maxLength={CODE_LENGTH}
                aria-label={`Dígito ${index + 1}`}
                disabled={busy}
              />
            ))}
          </div>
          {sent.dev_code && (
            <div className="dev-hint">
              Modo desarrollo (sin proveedor SMS): tu código es <strong>{sent.dev_code}</strong>
            </div>
          )}
          {error && <div className="alert alert-error">{error}</div>}
          <button
            type="button"
            className="btn-block"
            disabled={busy || digits.some((d) => !d)}
            onClick={() => verify(digits.join(""))}
          >
            {busy && <span className="spinner" />} Verificar e ingresar
          </button>
          <div className="auth-links">
            <button type="button" className="link-btn" disabled={cooldown > 0 || busy} onClick={() => requestCode()}>
              {cooldown > 0 ? `Reenviar código en ${cooldown} s` : "Reenviar código"}
            </button>
            <span className="sep">·</span>
            <button type="button" className="link-btn" onClick={() => { setSent(null); setError(null); }}>
              Cambiar datos
            </button>
          </div>
        </div>
      )}
    </AuthLayout>
  );
}
