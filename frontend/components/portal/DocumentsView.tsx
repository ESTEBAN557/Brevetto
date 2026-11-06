"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { clientApi } from "@/lib/client-api";
import type { DocumentCategorySlug, PortalDocument } from "@/lib/client-types";
import { formatDate, formatDateTime } from "@/lib/format";
import { Empty, ErrorBox, Loading } from "../DataState";
import { Icon } from "./Icon";
import { MONTHS, PageHead, PdfIcon, SearchBox, monthYearLabel, useDebounced } from "./ui";
import { usePortal } from "./PortalShell";

type Variant = "estados" | "facturas" | "certificados" | "contratos";

const CONFIG: Record<DocumentCategorySlug, { variant: Variant; title: string; crumb: string; empty: string }> = {
  "estados-de-cuenta": {
    variant: "estados",
    title: "Estados de cuenta",
    crumb: "Estados de cuenta",
    empty: "Aún no hay estados de cuenta publicados para este contrato.",
  },
  facturas: {
    variant: "facturas",
    title: "Facturas electrónicas",
    crumb: "Facturas",
    empty: "Aún no hay facturas publicadas para este contrato.",
  },
  certificados: {
    variant: "certificados",
    title: "Certificados de retención",
    crumb: "Certificados",
    empty: "No hay certificados para el año seleccionado.",
  },
  contratos: {
    variant: "contratos",
    title: "Contratos de arrendamiento",
    crumb: "Contratos",
    empty: "No hay contratos publicados en el expediente.",
  },
};

function DownloadButton({ doc, soft = false }: { doc: PortalDocument; soft?: boolean }) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      className={`icon-btn${soft ? " soft" : ""}`}
      title="Descargar"
      aria-label={`Descargar ${doc.title}`}
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await clientApi.downloadDocument(doc.id);
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? <span className="spinner" /> : <Icon name="cloudDownload" />}
    </button>
  );
}

function docName(doc: PortalDocument, prefix: string): string {
  const label = monthYearLabel(doc.document_date);
  return label ? `${prefix} ${label}` : doc.title;
}

export function DocumentsView({ category }: { category: DocumentCategorySlug }) {
  const { contract, me } = usePortal();
  const config = CONFIG[category];
  const thisYear = new Date().getFullYear();
  const [year, setYear] = useState(config.variant === "certificados" ? String(thisYear) : "");
  const [month, setMonth] = useState("");
  const [search, setSearch] = useState("");
  const [contractFilter, setContractFilter] = useState("");
  const [page, setPage] = useState(1);
  const [docs, setDocs] = useState<PortalDocument[] | null>(null);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const debounced = useDebounced(search);

  const contractId = config.variant === "contratos" ? contractFilter || contract?.id : contract?.id;

  const load = useCallback(() => {
    if (!contractId) return;
    setDocs(null);
    setError(null);
    clientApi
      .documents(category, {
        contract: contractId,
        year: year || undefined,
        month: month || undefined,
        q: debounced.trim() || undefined,
        page,
      })
      .then((data) => {
        setDocs(data.results);
        setCount(data.count);
      })
      .catch(() => setError("No fue posible cargar los documentos."));
  }, [category, contractId, year, month, debounced, page]);

  useEffect(load, [load]);
  useEffect(() => setPage(1), [year, month, debounced, contractId]);

  const years = useMemo(() => Array.from({ length: 6 }, (_, i) => String(thisYear - i)), [thisYear]);

  const filters = (
    <div className="pfilters">
      {config.variant !== "contratos" && (
        <select value={year} onChange={(e) => setYear(e.target.value)} aria-label="Año">
          {config.variant !== "certificados" && <option value="">Año</option>}
          {years.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      )}
      {(config.variant === "estados" || config.variant === "facturas") && (
        <select value={month} onChange={(e) => setMonth(e.target.value)} aria-label="Mes">
          <option value="">Mes</option>
          {MONTHS.map((name, i) => (
            <option key={name} value={i + 1}>{name}</option>
          ))}
        </select>
      )}
      {(config.variant === "estados" || config.variant === "facturas") && (
        <SearchBox value={search} onChange={setSearch} />
      )}
    </div>
  );

  let body: React.ReactNode;
  if (!contractId) body = <Empty>No tienes contratos vigentes asociados a tu cuenta.</Empty>;
  else if (error) body = <ErrorBox message={error} />;
  else if (!docs) body = <Loading />;
  else if (docs.length === 0) body = <Empty>{config.empty}</Empty>;
  else if (config.variant === "estados") {
    body = (
      <div className="plist">
        <div className="plist-head cols-ec"><span>Radicado</span><span>Nombre del estado de cuenta</span><span className="right">Acciones</span></div>
        {docs.map((doc) => {
          const open = expanded === doc.id;
          return (
            <Fragment key={doc.id}>
              <div className="prow cols-ec">
                <span className="code"><PdfIcon />{doc.filing_number}</span>
                <span>{docName(doc, "Estado de cuenta")}</span>
                <span className="pactions">
                  <DownloadButton doc={doc} />
                  <button
                    type="button"
                    className={`exp-toggle${open ? " open" : ""}`}
                    onClick={() => setExpanded(open ? null : doc.id)}
                    aria-expanded={open}
                    aria-label="Ver detalle"
                  >
                    <Icon name="chevronRight" />
                  </button>
                </span>
              </div>
              {open && (
                <div className="kv-grid">
                  <div>
                    <div className="kv-title">Información de beneficiario:</div>
                    <dl className="kv">
                      <div><dt>Nombre</dt><dd>{doc.detail.beneficiary.name}</dd></div>
                      <div><dt>Tipo de identificación</dt><dd>{doc.detail.beneficiary.identification_type}</dd></div>
                      <div><dt>Número de identificación</dt><dd>{doc.detail.beneficiary.identification_number}</dd></div>
                      <div><dt>Correo</dt><dd>{doc.detail.beneficiary.email}</dd></div>
                    </dl>
                  </div>
                  <div>
                    <div className="kv-title">Información del documento:</div>
                    <dl className="kv">
                      <div><dt>Radicado</dt><dd>{doc.detail.transaction.filing_number}</dd></div>
                      <div><dt>Fecha del documento</dt><dd>{formatDate(doc.detail.transaction.document_date)}</dd></div>
                      <div><dt>Registrado</dt><dd>{formatDateTime(doc.detail.transaction.registered_at)}</dd></div>
                      <div><dt>Origen</dt><dd>{doc.detail.transaction.channel}</dd></div>
                    </dl>
                  </div>
                </div>
              )}
            </Fragment>
          );
        })}
      </div>
    );
  } else if (config.variant === "facturas") {
    body = (
      <div className="plist">
        <div className="plist-head cols-inv-lite"><span>Tipo</span><span>Radicado</span><span>Descripción</span><span>Fecha</span><span className="right">Acciones</span></div>
        {docs.map((doc) => (
          <div key={doc.id} className="prow cols-inv-lite">
            <span>{doc.document_type_name}</span>
            <span className="code">{doc.filing_number}</span>
            <span>{docName(doc, "Factura")}</span>
            <span>{formatDate(doc.document_date)}</span>
            <span className="pactions"><DownloadButton doc={doc} /></span>
          </div>
        ))}
      </div>
    );
  } else {
    body = (
      <div className="plist">
        {docs.map((doc) => (
          <div key={doc.id} className="prow" style={{ gridTemplateColumns: "auto 1fr auto" }}>
            <PdfIcon />
            <span>
              <strong>{config.variant === "certificados" ? docName(doc, "Certificado de retención") : doc.title}</strong>
              <br />
              <small className="muted">{doc.filing_number} · {formatDate(doc.document_date)}</small>
            </span>
            <button
              type="button"
              className="btn-ink-pill"
              onClick={() => clientApi.downloadDocument(doc.id)}
            >
              <Icon name="download" size={18} /> Descargar
            </button>
          </div>
        ))}
      </div>
    );
  }

  const pages = Math.max(1, Math.ceil(count / 25));

  return (
    <>
      <PageHead
        crumbs={[{ label: "Inicio", href: "/portal" }, { label: "Documentos" }, { label: config.crumb }]}
        title={config.title}
      >
        {filters}
      </PageHead>
      {config.variant === "contratos" && me.contracts.length > 1 && (
        <div className="pcard" style={{ marginBottom: "1rem", display: "flex", gap: "1rem", alignItems: "center" }}>
          <label htmlFor="contract-pick" style={{ fontFamily: "var(--font-ui)", fontWeight: 600, color: "var(--stamp)" }}>
            Contrato:
          </label>
          <select id="contract-pick" value={contractId ?? ""} onChange={(e) => setContractFilter(e.target.value)}>
            {me.contracts.map((c) => (
              <option key={c.id} value={c.id}>{c.property_address} · [{c.contract_number}]</option>
            ))}
          </select>
        </div>
      )}
      <div className="pcard">
        {body}
        {docs && count > 25 && (
          <div className="pagination">
            <span>{count} documentos</span>
            <span className="row">
              <button type="button" className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
              <span>Página {page} de {pages}</span>
              <button type="button" className="btn-secondary btn-sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Siguiente</button>
            </span>
          </div>
        )}
      </div>
    </>
  );
}
