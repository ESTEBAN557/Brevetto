"use client";

import Link from "next/link";
import QRCode from "qrcode";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ErrorBox } from "@/components/DataState";
import { FileDrop } from "@/components/FileDrop";
import { FilingStamp } from "@/components/FilingStamp";
import { Modal, printModal } from "@/components/Modal";
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
  const [showVoucher, setShowVoucher] = useState(false);

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
        <div className="brand-lockup" style={{ marginBottom: 0 }}>
          <div className="brand-chip">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
          </div>
          <div>
            <div className="kicker">Portal de radicación web</div>
            <h1 style={{ margin: 0 }}>Radicación de documentos</h1>
            <p className="small">Inquilinos y propietarios: radique directamente en el expediente de su contrato.</p>
          </div>
        </div>
        <Link href="/" className="small">
          Inicio
        </Link>
      </div>

      <Stepper step={step} />

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
              <div className="receipt-brand">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
                <div className="receipt-kicker">Sistema de Gestión Documental Brevetto</div>
                <h2 style={{ margin: "0.25rem 0 0" }}>Comprobante de radicación</h2>
              </div>
              <div className="right">
                <div className="receipt-kicker">Número de radicado</div>
                <div className="filing">{receipt.filing_number}</div>
              </div>
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
            <button type="button" onClick={() => setShowVoucher(true)}>
              Previsualizar comprobante oficial
            </button>
            <button type="button" className="btn-secondary" onClick={() => window.print()}>
              Imprimir esta página
            </button>
            <button type="button" className="btn-secondary" onClick={() => { setStep(2); setFiles([]); setReceipt(null); }}>
              Radicar otro documento
            </button>
            <button type="button" className="btn-ghost" onClick={reset}>
              Finalizar
            </button>
          </div>

          {showVoucher && (
            <Modal
              size="narrow"
              title="Comprobante Oficial de Radicación"
              onClose={() => setShowVoucher(false)}
              footer={
                <>
                  <button type="button" className="btn-secondary" onClick={() => setShowVoucher(false)}>
                    Cerrar
                  </button>
                  <button type="button" onClick={printModal}>
                    Imprimir / guardar como PDF
                  </button>
                </>
              }
            >
              <OfficialVoucher receipt={receipt} />
            </Modal>
          )}
        </div>
      )}
    </main>
  );
}

/** Stepper visual de 3 pasos del portal. */
function Stepper({ step }: { step: Step }) {
  const items = [
    { n: 1, label: "Validar contrato", sub: "Número de contrato y NIT / cédula" },
    { n: 2, label: "Cargar documento", sub: "PDF o imagen, hasta 25 MB" },
    { n: 3, label: "Comprobante", sub: "Radicado oficial imprimible" },
  ];
  return (
    <div className="stepper no-print" aria-label="Progreso de la radicación">
      {items.map((item) => {
        const state = step === item.n ? "active" : step > item.n ? "done" : "";
        return (
          <div key={item.n} className={`step ${state}`}>
            <div className="circle">{state === "done" ? "✓" : item.n}</div>
            <div className="label">{item.label}</div>
            <div className="sub">{item.sub}</div>
          </div>
        );
      })}
    </div>
  );
}

/** Código QR de verificación del comprobante (radicado + huella + firma). */
function VerificationQr({ receipt }: { receipt: PortalReceipt }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    const payload = [
      "BREVETTO",
      receipt.filing_number,
      receipt.contract_number,
      `sha256:${receipt.file_hash}`,
      `sig:${receipt.receipt_signature}`,
      receipt.received_at,
    ].join("|");
    QRCode.toDataURL(payload, { errorCorrectionLevel: "M", margin: 1, width: 224, color: { dark: "#161513", light: "#ffffff" } })
      .then(setSrc)
      .catch(() => setSrc(null));
  }, [receipt]);
  if (!src) return <div className="qr" aria-hidden />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img className="qr" src={src} alt={`Código QR de verificación del radicado ${receipt.filing_number}`} />;
}

/** Comprobante oficial (US-019): documento imprimible con sello de radicación y QR verificable. */
function OfficialVoucher({ receipt }: { receipt: PortalReceipt }) {
  const receivedDate = receipt.received_at.slice(0, 10).split("-").reverse().join("/");
  return (
    <div className="receipt" style={{ borderWidth: 3 }}>
      <div className="seal" aria-hidden>
        <span>Coltebienes S.A.</span>
        <strong>Radicado</strong>
        <small>{receivedDate}</small>
        <span>Brevetto</span>
      </div>
      <div className="receipt-head">
        <div className="receipt-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
          <div className="receipt-kicker">Sistema de Gestión Documental Brevetto · Portal de Radicación Web</div>
          <h2 style={{ margin: "0.25rem 0 0" }}>Comprobante Oficial de Radicación</h2>
        </div>
        <div className="right" style={{ paddingRight: 150 }}>
          <div className="receipt-kicker">Número de radicado</div>
          <FilingStamp value={receipt.filing_number} size="lg" plain />
        </div>
      </div>
      <dl>
        <dt>Fecha y hora de recepción</dt>
        <dd>{receipt.received_at_display}</dd>
        <dt>Contrato</dt>
        <dd className="mono">{receipt.contract_number}</dd>
        <dt>Titular del contrato</dt>
        <dd>{receipt.client_name}</dd>
        <dt>Tipo de documento</dt>
        <dd>{receipt.document_type}</dd>
        <dt>Archivo recibido</dt>
        <dd>
          {receipt.original_filename} ({formatBytes(receipt.file_size_bytes)})
        </dd>
        <dt>Radicado por</dt>
        <dd>{receipt.sender_name}</dd>
        <dt>Estado</dt>
        <dd>Recibido · en verificación por Coltebienes</dd>
        <dt>Huella digital SHA-256</dt>
        <dd className="mono small">{receipt.file_hash}</dd>
        <dt>Firma digital del comprobante</dt>
        <dd className="mono small">{receipt.receipt_signature}</dd>
      </dl>
      <div className="receipt-foot">
        <p className="small muted" style={{ margin: 0, maxWidth: 420 }}>
          Este comprobante certifica la recepción del documento en la fecha y hora indicadas. Su autenticidad puede
          verificarse con el número de radicado, la huella SHA-256, la firma digital o escaneando el código QR.
          Generado electrónicamente por Brevetto.
        </p>
        <div className="right">
          <VerificationQr receipt={receipt} />
          <div className="small muted" style={{ marginTop: 4 }}>Verificación</div>
        </div>
      </div>
    </div>
  );
}
