"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ContractPicker } from "@/components/ContractPicker";
import { ErrorBox } from "@/components/DataState";
import { FileDrop } from "@/components/FileDrop";
import { StatusBadge } from "@/components/StatusBadge";
import { documentsApi } from "@/lib/api";
import type { Contract, ProcessingStatus, SourceChannel } from "@/lib/types";

interface ReceiptRow {
  id: string;
  filing_number: string;
  filename: string;
  status: ProcessingStatus;
}

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [channel, setChannel] = useState<SourceChannel>("FISICO_ESCANEADO");
  const [contract, setContract] = useState<Contract | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipts, setReceipts] = useState<ReceiptRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!files.length) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("source_channel", channel);
      if (contract) form.append("contract_id", contract.id);

      if (files.length === 1) {
        form.append("file", files[0]);
        const receipt = await documentsApi.upload(form);
        setReceipts([
          { id: receipt.id, filing_number: receipt.filing_number, filename: receipt.original_filename, status: receipt.processing_status },
          ...receipts,
        ]);
        setMessage(`Documento radicado con el número ${receipt.filing_number}. El análisis con IA se ejecuta en segundo plano.`);
      } else {
        files.forEach((file) => form.append("files", file));
        const batch = await documentsApi.batchUpload(form);
        setReceipts([...batch.items.map((i) => ({ id: i.id, filing_number: i.filing_number, filename: i.filename, status: i.status })), ...receipts]);
        setMessage(batch.message);
      }
      setFiles([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error radicando los documentos");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Radicar documentos</h1>
          <p>Escaneos físicos o archivos digitales. Cada archivo recibe un radicado único y entra a la cola de clasificación.</p>
        </div>
      </div>

      <div className="split">
        <form className="card stack" onSubmit={handleSubmit}>
          <FileDrop files={files} onChange={setFiles} multiple />
          <div className="form-grid">
            <label className="field">
              Canal de origen
              <select value={channel} onChange={(e) => setChannel(e.target.value as SourceChannel)}>
                <option value="FISICO_ESCANEADO">Documento físico escaneado</option>
                <option value="DIGITAL_INTERNO">Digital cargado por personal</option>
                <option value="CORREO">Recibido por correo electrónico</option>
              </select>
            </label>
            <label className="field">
              Contrato (opcional)
              <span className="hint">Si lo conoce, el documento se archiva directamente en su expediente.</span>
            </label>
          </div>
          <ContractPicker value={contract} onChange={setContract} />
          <ErrorBox message={error} />
          {message && <div className="alert alert-success">{message}</div>}
          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={() => setFiles([])} disabled={!files.length || busy}>
              Limpiar
            </button>
            <button type="submit" disabled={!files.length || busy}>
              {busy && <span className="spinner" />}
              {files.length > 1 ? `Radicar ${files.length} documentos` : "Radicar documento"}
            </button>
          </div>
        </form>

        <div className="card">
          <div className="card-title">
            <h2>Comprobantes de esta sesión</h2>
            <Link href="/admin" className="small">
              Ver bandeja
            </Link>
          </div>
          {receipts.length === 0 ? (
            <p className="muted">Aún no ha radicado documentos en esta sesión.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Radicado</th>
                  <th>Archivo</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {receipts.map((r) => (
                  <tr key={r.id}>
                    <td className="mono">
                      <Link href={`/admin/documents/${r.id}`}>{r.filing_number}</Link>
                    </td>
                    <td className="truncate" style={{ maxWidth: 200 }}>
                      {r.filename}
                    </td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </main>
  );
}
