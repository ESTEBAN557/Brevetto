"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Empty, ErrorBox, Loading } from "@/components/DataState";
import { Modal } from "@/components/Modal";
import { AttachmentDrop } from "@/components/portal/AttachmentDrop";
import { Icon } from "@/components/portal/Icon";
import { usePortal } from "@/components/portal/PortalShell";
import { PageHead, SearchBox, useDebounced } from "@/components/portal/ui";
import { ApiError } from "@/lib/api";
import { clientApi } from "@/lib/client-api";
import type { CatalogEntry, ServiceRequestSummary } from "@/lib/client-types";
import { formatDateTime } from "@/lib/format";

export default function RequestsPage() {
  const [items, setItems] = useState<ServiceRequestSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const debounced = useDebounced(search);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("crear")) setCreating(true);
  }, []);

  useEffect(() => {
    setItems(null);
    clientApi
      .requests(debounced.trim() || undefined)
      .then(setItems)
      .catch(() => setError("No fue posible cargar tus requerimientos."));
  }, [debounced]);

  return (
    <>
      <PageHead
        crumbs={[{ label: "Inicio", href: "/portal" }, { label: "Requerimientos" }]}
        title="Requerimientos"
        subtitle="Envía tu solicitud, queja o sugerencia y monitorea el progreso hasta su resolución."
      />
      <div className="row row-between" style={{ marginBottom: "1rem" }}>
        <SearchBox value={search} onChange={setSearch} />
        <button type="button" className="btn-ink-pill" onClick={() => setCreating(true)}>
          <Icon name="plus" size={18} /> Crear requerimiento
        </button>
      </div>
      <div className="pcard">
        <ErrorBox message={error} />
        {!items && !error && <Loading />}
        {items && items.length === 0 && <Empty>{search ? "Sin resultados para tu búsqueda." : "Aún no has creado requerimientos."}</Empty>}
        {items && items.length > 0 && (
          <div className="plist">
            <div className="plist-head cols-req">
              <span>Radicado</span><span>Asunto</span><span>Creación</span><span>Servicio</span><span>Subcategoría</span>
              <span>Asesor asignado</span><span>Estado</span><span className="right">Acciones</span>
            </div>
            {items.map((item) => (
              <div key={item.id} className="prow cols-req">
                <Link href={`/portal/requerimientos/${item.id}`} className="link-id">#{item.id}</Link>
                <Link href={`/portal/requerimientos/${item.id}`} className="link-subject">{item.subject}</Link>
                <span className="small">{formatDateTime(item.created_at)}</span>
                <span>{item.service}</span>
                <span>{item.subcategory}</span>
                <span>{item.assigned_to || "Por asignar"}</span>
                <span><span className={`rstatus ${item.status}`}>{item.status_display}</span></span>
                <span className="pactions">
                  <Link href={`/portal/requerimientos/${item.id}`} className="icon-btn soft" aria-label="Ver requerimiento">
                    <Icon name="eye" />
                  </Link>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      {creating && <NewRequestModal onClose={() => setCreating(false)} />}
    </>
  );
}

function NewRequestModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { me, contract } = usePortal();
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState<CatalogEntry | null>(null);
  const [fullList, setFullList] = useState(false);
  const [contractId, setContractId] = useState(contract?.id ?? "");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    clientApi.catalog().then(setCatalog).catch(() => setError("No fue posible cargar el catálogo de casos."));
  }, []);

  const matches = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return [];
    return catalog
      .filter((c) => `${c.case_type} ${c.service} ${c.subcategory}`.toLowerCase().includes(term))
      .slice(0, 6);
  }, [catalog, query]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!chosen) {
      setError("Elige el tipo de caso que mejor describa tu requerimiento.");
      return;
    }
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.set("contract", contractId);
    form.set("catalog_id", String(chosen.id));
    form.set("subject", subject);
    form.set("description", description);
    files.forEach((file) => form.append("files", file));
    try {
      const created = await clientApi.createRequest(form);
      router.push(`/portal/requerimientos/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No fue posible crear el requerimiento.");
      setBusy(false);
    }
  }

  return (
    <Modal title={<span className="modal-title-ink">Datos del caso</span>} onClose={onClose} size="wide">
      <form onSubmit={submit}>
        <div className="new-req-grid">
          <div className="stack">
            {chosen ? (
              <div className="selected-case">
                <span>
                  <strong>{chosen.subcategory}</strong>
                  <br />
                  <span className="muted small">{chosen.case_type} · {chosen.service}</span>
                </span>
                <button type="button" className="btn-ghost btn-sm" onClick={() => setChosen(null)}>Cambiar</button>
              </div>
            ) : fullList ? (
              <label className="field">
                Tipo de caso
                <select value="" onChange={(e) => setChosen(catalog.find((c) => c.id === Number(e.target.value)) ?? null)}>
                  <option value="">Elige de la lista…</option>
                  {catalog.map((c) => (
                    <option key={c.id} value={c.id}>{c.case_type} · {c.service} · {c.subcategory}</option>
                  ))}
                </select>
              </label>
            ) : (
              <div className="sugg">
                <label className="psearch" style={{ display: "block" }}>
                  <Icon name="search" size={18} />
                  <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="¿Qué necesitas reportar?" autoComplete="off" />
                </label>
                {matches.length > 0 && (
                  <div className="sugg-list">
                    {matches.map((c) => (
                      <button key={c.id} type="button" onClick={() => setChosen(c)}>
                        {c.subcategory}
                        <small>{c.case_type} · {c.service}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {!chosen && (
              <>
                <p className="muted small" style={{ margin: 0 }}>
                  Escribe en tus palabras y elige la opción que más se parezca. Completamos tipo, servicio y subcategoría por ti.
                </p>
                <button type="button" className="link-btn" style={{ alignSelf: "flex-start" }} onClick={() => setFullList((v) => !v)}>
                  {fullList ? "Buscar por palabras" : "¿No encuentras tu caso? Elegir de la lista completa"}
                </button>
              </>
            )}
            <label className="field">
              Inmueble *
              <select value={contractId} onChange={(e) => setContractId(e.target.value)} required>
                {me.contracts.map((c) => (
                  <option key={c.id} value={c.id}>{c.property_address} · [{c.contract_number}]</option>
                ))}
              </select>
            </label>
            <label className="field">
              Asunto *
              <input value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} required />
            </label>
            <label className="field">
              Descripción del caso *
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} maxLength={5000} required />
            </label>
          </div>
          <div>
            <div className="row row-between" style={{ marginBottom: "0.5rem" }}>
              <strong style={{ color: "var(--stamp)", fontFamily: "var(--font-ui)" }}>Adjuntos</strong>
              <span className="muted small">Opcional</span>
            </div>
            <AttachmentDrop files={files} onChange={setFiles} />
          </div>
        </div>
        <ErrorBox message={error} />
        <div className="form-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" disabled={busy || !contractId}>
            {busy && <span className="spinner" />} Crear requerimiento
          </button>
        </div>
      </form>
    </Modal>
  );
}
