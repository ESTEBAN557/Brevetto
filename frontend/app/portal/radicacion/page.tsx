"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { ErrorBox } from "@/components/DataState";
import { FileDrop } from "@/components/FileDrop";
import { ApiError, portalApi } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import type { PortalReceipt, PortalSession } from "@/lib/types";

type Step = 1 | 2 | 3;

export default function PortalFilingPage() {
  const [step, setStep] = useState<Step>(1);
  const [contractNumber, setContractNumber] = useState("");
  const [identification, setIdentification] = useState("");
  const [session, setSession] = useState<PortalSession | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [typeCode, setTypeCode] = useState("");
  const [senderName, setSenderName] = useState("");
  const [expiration, setExpiration] = useState("");
  const [receipt, setReceipt] = useState<PortalReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selectedType = useMemo(() => session?.document_types.find((t) => t.code === typeCode), [session, typeCode]);

  async function verify(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await portalApi.verify(contractNumber.trim(), identification.trim());
      setSession(data);
      setStep(2);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? "No encontramos un contrato vigente con esos datos. Verifique el número de contrato y su NIT o cédula."
          : err instanceof ApiError && err.status === 429
            ? "Demasiados intentos. Espere unos minutos e intente de nuevo."
            : "No fue posible validar el contrato en este momento.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!session || !files.length) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", files[0]);
      form.append("document_type_code", typeCode);
      form.append("sender_name", senderName.trim());
      if (expiration) form.append("expiration_date", expiration);
      const data = await portalApi.submit(session.portal_token, form);
      setReceipt(data);
      setStep(3);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Su sesión expiró. Valide nuevamente su contrato."
          : err instanceof Error
            ? err.message
            : "No fue posible radicar el documento.",
      );
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setStep(1);
    setSession(null);
    setFiles([]);
    setTypeCode("");
    setSenderName("");
    setExpiration("");
    setReceipt(null);
    setError(null);
  }

  return (
    <main className="page page-narrow">
      <div className="page-header no-print">
        <div>
          <h1>Radicación de documentos · Coltebienes S.A.</h1>
          <p>Portal para inquilinos y propietarios. Radique documentos directamente en el expediente de su contrato.</p>
        </div>
        <Link href="/" className="small">
          Inicio
        </Link>
      </div>

      <div className="steps no-print">
        <span className={step === 1 ? "active" : "done"}>1. Validar contrato</span>
        <span className={step === 2 ? "active" : step > 2 ? "done" : ""}>2. Cargar documento</span>
        <span className={step === 3 ? "active" : ""}>3. Comprobante</span>
      </div>

      {step === 1 && (
        <form className="card stack" onSubmit={verify}>
          <label className="field">
            Número de contrato
            <input value={contractNumber} onChange={(e) => setContractNumber(e.target.value)} placeholder="CONT-2026-042" required />
          </label>
          <label className="field">
            NIT o cédula del titular
            <span className="hint">Puede escribirlo con o sin puntos y guion.</span>
            <input value={identification} onChange={(e) => setIdentification(e.target.value)} placeholder="900.123.456-1" required />
          </label>
          <ErrorBox message={error} />
          <div className="form-actions">
            <button type="submit" disabled={busy}>
              {busy && <span className="spinner" />} Validar
            </button>
          </div>
        </form>
      )}

      {step === 2 && session && (
        <div className="stack">
          <section className="card">
            <div className="card-title">
              <h3>Contrato validado</h3>
              <button type="button" className="btn-ghost btn-sm" onClick={reset}>
                Cambiar contrato
              </button>
            </div>
            <dl className="suggestion">
              <dt>Contrato</dt>
              <dd className="mono">{session.contract.contract_number}</dd>
              <dt>Titular</dt>
              <dd>
                {session.client.name} <span className="muted">({session.client.identification_number})</span>
              </dd>
              <dt>Inmueble</dt>
              <dd>{session.contract.property_address}</dd>
              <dt>Vigencia</dt>
              <dd>
                {formatDate(session.contract.start_date)} → {formatDate(session.contract.end_date)}
              </dd>
            </dl>
            {session.expiring_documents.length > 0 && (
              <div className="alert alert-warning" style={{ marginTop: "0.75rem" }}>
                Documentos vencidos o por vencer:{" "}
                {session.expiring_documents
                  .map((d) => `${d.document_type ?? d.filing_number} (${formatDate(d.expiration_date)}${d.expired ? ", vencido" : ""})`)
                  .join(" · ")}
              </div>
            )}
          </section>

          <form className="card stack" onSubmit={submit}>
            <h3>Documento a radicar</h3>
            <FileDrop files={files} onChange={setFiles} multiple={false} />
            <label className="field">
              Tipo de documento
              <select value={typeCode} onChange={(e) => setTypeCode(e.target.value)} required>
                <option value="">Seleccione…</option>
                {session.document_types.map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            {selectedType?.requires_expiration && (
              <label className="field">
                Fecha de vencimiento del documento
                <input type="date" value={expiration} onChange={(e) => setExpiration(e.target.value)} required />
              </label>
            )}
            <label className="field">
              Nombre de quien radica
              <input value={senderName} onChange={(e) => setSenderName(e.target.value)} required placeholder="Nombre completo" />
            </label>
            <ErrorBox message={error} />
            <div className="form-actions">
              <button type="submit" disabled={busy || !files.length || !typeCode}>
                {busy && <span className="spinner" />} Radicar documento
              </button>
            </div>
          </form>
        </div>
      )}

      {step === 3 && receipt && (
        <div className="stack">
          <div className="receipt">
            <div className="receipt-head">
              <div>
                <h2>Comprobante de radicación</h2>
                <div className="muted small">Coltebienes S.A. · Sistema de Gestión Documental Brevetto</div>
              </div>
              <div className="filing">{receipt.filing_number}</div>
            </div>
            <dl>
              <dt>Fecha y hora de radicación</dt>
              <dd>{receipt.received_at_display}</dd>
              <dt>Contrato</dt>
              <dd>{receipt.contract_number}</dd>
              <dt>Titular</dt>
              <dd>{receipt.client_name}</dd>
              <dt>Tipo de documento</dt>
              <dd>{receipt.document_type}</dd>
              <dt>Archivo</dt>
              <dd>
                {receipt.original_filename} ({formatBytes(receipt.file_size_bytes)})
              </dd>
              <dt>Radicado por</dt>
              <dd>{receipt.sender_name}</dd>
              <dt>Huella SHA-256</dt>
              <dd className="mono small">{receipt.file_hash}</dd>
              <dt>Firma digital</dt>
              <dd className="mono small">{receipt.receipt_signature}</dd>
            </dl>
            <p className="small muted" style={{ marginTop: "1rem" }}>
              Este comprobante certifica la recepción del documento. Coltebienes verificará su contenido y lo incorporará al
              expediente del contrato. Conserve el número de radicado para cualquier consulta.
            </p>
          </div>
          <div className="row no-print">
            <button type="button" onClick={() => window.print()}>
              Descargar / imprimir comprobante
            </button>
            <button type="button" className="btn-secondary" onClick={() => { setStep(2); setFiles([]); setReceipt(null); }}>
              Radicar otro documento
            </button>
            <button type="button" className="btn-ghost" onClick={reset}>
              Finalizar
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
