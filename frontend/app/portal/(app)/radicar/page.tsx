"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ErrorBox } from "@/components/DataState";
import { FileDrop } from "@/components/FileDrop";
import { FilingStamp } from "@/components/FilingStamp";
import { usePortal } from "@/components/portal/PortalShell";
import { PageHead } from "@/components/portal/ui";
import { ApiError } from "@/lib/api";
import { clientApi } from "@/lib/client-api";
import type { DocumentType } from "@/lib/types";

type Receipt = Awaited<ReturnType<typeof clientApi.uploadDocument>>;

/** Radicación directa del cliente autenticado: el documento queda en el expediente de su contrato. */
export default function FilePage() {
  const { contract } = usePortal();
  const [types, setTypes] = useState<DocumentType[]>([]);
  const [typeCode, setTypeCode] = useState("");
  const [documentDate, setDocumentDate] = useState("");
  const [expiration, setExpiration] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState<Receipt | null>(null);

  useEffect(() => {
    clientApi.documentTypes().then((data) => setTypes(data.document_types)).catch(() => setError("No fue posible cargar los tipos de documento."));
  }, []);

  const selected = types.find((t) => t.code === typeCode);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!contract || files.length === 0) return;
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.set("contract", contract.id);
    form.set("document_type", typeCode);
    form.set("file", files[0]);
    if (documentDate) form.set("document_date", documentDate);
    if (expiration) form.set("expiration_date", expiration);
    try {
      setReceipt(await clientApi.uploadDocument(form));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No fue posible radicar el documento.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead
        crumbs={[{ label: "Inicio", href: "/portal" }, { label: "Radicar documento" }]}
        title="Radicar documento"
        subtitle="Envía pólizas, certificados o comunicaciones al expediente digital de tu contrato."
      />
      {receipt ? (
        <div className="pcard stack" style={{ maxWidth: 640 }}>
          <div className="alert alert-success">Documento radicado correctamente. Nuestro equipo lo validará en breve.</div>
          <div><span className="muted small">Número de radicado</span><br /><FilingStamp value={receipt.filing_number} size="lg" /></div>
          <dl className="dl">
            <div><dt>Contrato</dt><dd>{receipt.contract_number}</dd></div>
            <div><dt>Tipo declarado</dt><dd>{receipt.document_type}</dd></div>
            <div><dt>Archivo</dt><dd>{receipt.original_filename}</dd></div>
            <div><dt>Recibido</dt><dd>{receipt.received_at_display}</dd></div>
          </dl>
          <div className="row">
            <button type="button" onClick={() => { setReceipt(null); setFiles([]); setTypeCode(""); }}>Radicar otro documento</button>
            <Link href="/portal" className="btn btn-secondary">Volver al inicio</Link>
          </div>
        </div>
      ) : (
        <form className="pcard stack" style={{ maxWidth: 720 }} onSubmit={submit}>
          {contract && (
            <div className="alert alert-info">
              Contrato <strong>{contract.contract_number}</strong> · {contract.property_address}
            </div>
          )}
          <div className="form-grid">
            <label className="field">
              Tipo de documento *
              <select value={typeCode} onChange={(e) => setTypeCode(e.target.value)} required>
                <option value="">Selecciona…</option>
                {types.map((t) => (
                  <option key={t.code} value={t.code}>{t.name}</option>
                ))}
              </select>
            </label>
            <label className="field">
              Fecha del documento
              <input type="date" value={documentDate} onChange={(e) => setDocumentDate(e.target.value)} />
            </label>
            {selected?.requires_expiration && (
              <label className="field">
                Fecha de vencimiento *
                <input type="date" value={expiration} onChange={(e) => setExpiration(e.target.value)} required />
              </label>
            )}
          </div>
          <FileDrop files={files} onChange={setFiles} multiple={false} />
          <ErrorBox message={error} />
          <div className="form-actions">
            <button type="submit" disabled={busy || !contract || files.length === 0 || !typeCode}>
              {busy && <span className="spinner" />} Radicar documento
            </button>
          </div>
        </form>
      )}
    </>
  );
}
