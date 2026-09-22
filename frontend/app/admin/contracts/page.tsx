"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ErrorBox, Empty, Loading } from "@/components/DataState";
import { NeutralBadge } from "@/components/StatusBadge";
import { clientsApi, contractsApi } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Client, Contract, Paginated } from "@/lib/types";

const EMPTY_FORM = {
  contract_number: "",
  property_address: "",
  start_date: "",
  end_date: "",
  status: "ACTIVO",
  client_id: "",
  new_client: false,
  client_name: "",
  client_document_type: "NIT",
  client_identification: "",
  client_email: "",
  client_phone: "",
  client_type: "JURIDICA",
};

export default function ContractsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [data, setData] = useState<Paginated<Contract> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [clientQuery, setClientQuery] = useState("");
  const [clientResults, setClientResults] = useState<Client[]>([]);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function load() {
    try {
      setData(await contractsApi.list({ search, status, ordering: "-created_at" }));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando contratos");
    }
  }

  useEffect(() => {
    const handle = window.setTimeout(load, 250);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, status]);

  useEffect(() => {
    if (form.new_client || clientQuery.trim().length < 2) {
      setClientResults([]);
      return;
    }
    const handle = window.setTimeout(async () => {
      try {
        setClientResults((await clientsApi.list({ search: clientQuery.trim() })).results);
      } catch {
        setClientResults([]);
      }
    }, 300);
    return () => window.clearTimeout(handle);
  }, [clientQuery, form.new_client]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      let clientId = selectedClient?.id ?? "";
      if (form.new_client) {
        const client = await clientsApi.create({
          name: form.client_name,
          document_type: form.client_document_type,
          identification_number: form.client_identification,
          email: form.client_email,
          phone: form.client_phone,
          client_type: form.client_type,
        });
        clientId = client.id;
      }
      if (!clientId) throw new Error("Seleccione un cliente existente o cree uno nuevo.");
      const contract = await contractsApi.create({
        contract_number: form.contract_number,
        client: clientId,
        property_address: form.property_address,
        start_date: form.start_date,
        end_date: form.end_date,
        status: form.status,
      });
      setShowForm(false);
      setForm(EMPTY_FORM);
      setSelectedClient(null);
      setClientQuery("");
      await load();
      setError(null);
      window.alert(`Contrato ${contract.contract_number} creado. Expediente: ${contract.digital_record?.storage_path}`);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "No fue posible crear el contrato");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <h1>Contratos y expedientes digitales</h1>
          <p>Cada contrato tiene un expediente electrónico único en el almacenamiento de objetos.</p>
        </div>
        <button type="button" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancelar" : "Nuevo contrato"}
        </button>
      </div>

      {showForm && (
        <form className="card stack" onSubmit={handleCreate} style={{ marginBottom: "1.25rem" }}>
          <h2>Registrar contrato</h2>
          <div className="form-grid">
            <label className="field">
              Número de contrato
              <input value={form.contract_number} onChange={(e) => setForm({ ...form, contract_number: e.target.value })} required placeholder="CONT-2026-045" />
            </label>
            <label className="field">
              Estado
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="ACTIVO">Activo</option>
                <option value="EN_RENOVACION">En renovación</option>
                <option value="TERMINADO">Terminado</option>
              </select>
            </label>
            <label className="field" style={{ gridColumn: "1 / -1" }}>
              Dirección del inmueble / bodega
              <input value={form.property_address} onChange={(e) => setForm({ ...form, property_address: e.target.value })} required />
            </label>
            <label className="field">
              Fecha de inicio
              <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required />
            </label>
            <label className="field">
              Fecha de fin
              <input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} required />
            </label>
          </div>

          <h3>Cliente</h3>
          <label className="row small">
            <input type="checkbox" checked={form.new_client} onChange={(e) => setForm({ ...form, new_client: e.target.checked })} />
            Crear un cliente nuevo
          </label>
          {form.new_client ? (
            <div className="form-grid">
              <label className="field">
                Nombre o razón social
                <input value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} required />
              </label>
              <label className="field">
                Tipo de persona
                <select value={form.client_type} onChange={(e) => setForm({ ...form, client_type: e.target.value })}>
                  <option value="JURIDICA">Persona jurídica</option>
                  <option value="NATURAL">Persona natural</option>
                </select>
              </label>
              <label className="field">
                Tipo de identificación
                <select value={form.client_document_type} onChange={(e) => setForm({ ...form, client_document_type: e.target.value })}>
                  <option value="NIT">NIT</option>
                  <option value="CC">Cédula de ciudadanía</option>
                  <option value="CE">Cédula de extranjería</option>
                  <option value="PASAPORTE">Pasaporte</option>
                </select>
              </label>
              <label className="field">
                Número de identificación
                <input value={form.client_identification} onChange={(e) => setForm({ ...form, client_identification: e.target.value })} required />
              </label>
              <label className="field">
                Correo electrónico
                <input type="email" value={form.client_email} onChange={(e) => setForm({ ...form, client_email: e.target.value })} required />
              </label>
              <label className="field">
                Teléfono
                <input value={form.client_phone} onChange={(e) => setForm({ ...form, client_phone: e.target.value })} />
              </label>
            </div>
          ) : selectedClient ? (
            <div className="picker-selected">
              <span>
                <strong>{selectedClient.name}</strong> · {selectedClient.identification_number}
              </span>
              <button type="button" className="btn-ghost btn-sm" onClick={() => setSelectedClient(null)}>
                Cambiar
              </button>
            </div>
          ) : (
            <div className="picker">
              <input placeholder="Buscar cliente por nombre o NIT…" value={clientQuery} onChange={(e) => setClientQuery(e.target.value)} />
              {clientResults.length > 0 && (
                <div className="picker-results">
                  {clientResults.map((c) => (
                    <button key={c.id} type="button" onClick={() => setSelectedClient(c)}>
                      {c.name}
                      <small>
                        {c.document_type} {c.identification_number} · {c.contracts_count} contrato(s)
                      </small>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <ErrorBox message={formError} />
          <div className="form-actions">
            <button type="submit" disabled={saving}>
              {saving && <span className="spinner" />} Crear contrato y expediente
            </button>
          </div>
        </form>
      )}

      <div className="card">
        <div className="card-title">
          <h2>Contratos</h2>
          <div className="row">
            <input placeholder="Buscar contrato, cliente, NIT o dirección…" value={search} onChange={(e) => setSearch(e.target.value)} style={{ width: 320 }} />
            <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ width: 180 }}>
              <option value="">Todos</option>
              <option value="ACTIVO">Activos</option>
              <option value="EN_RENOVACION">En renovación</option>
              <option value="TERMINADO">Terminados</option>
            </select>
          </div>
        </div>
        <ErrorBox message={error} />
        {!data && !error && <Loading />}
        {data && data.results.length === 0 && <Empty>No hay contratos que coincidan.</Empty>}
        {data && data.results.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Contrato</th>
                  <th>Cliente</th>
                  <th>Inmueble</th>
                  <th>Vigencia</th>
                  <th>Estado</th>
                  <th>Documentos</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.results.map((c) => (
                  <tr key={c.id}>
                    <td className="mono nowrap">{c.contract_number}</td>
                    <td>
                      {c.client_detail?.name}
                      <div className="small muted">{c.client_detail?.identification_number}</div>
                    </td>
                    <td className="truncate" style={{ maxWidth: 260 }}>
                      {c.property_address}
                    </td>
                    <td className="nowrap small">
                      {formatDate(c.start_date)} → {formatDate(c.end_date)}
                    </td>
                    <td>
                      <NeutralBadge>{c.status_label}</NeutralBadge>
                    </td>
                    <td>{c.digital_record?.documents_count ?? 0}</td>
                    <td className="right">
                      <Link href={`/admin/contracts/${c.id}`} className="btn btn-secondary btn-sm">
                        Abrir expediente
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
