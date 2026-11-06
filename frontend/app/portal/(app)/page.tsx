"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon } from "@/components/portal/Icon";
import { usePortal } from "@/components/portal/PortalShell";
import { Empty, ErrorBox } from "@/components/DataState";
import { clientApi } from "@/lib/client-api";
import type { PortalHome } from "@/lib/client-types";
import { formatDate } from "@/lib/format";

export default function PortalHomePage() {
  const { me, contract } = usePortal();
  const [home, setHome] = useState<PortalHome | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!contract) return;
    setHome(null);
    clientApi
      .home(contract.id)
      .then(setHome)
      .catch(() => setError("No fue posible cargar el resumen de tu contrato."));
  }, [contract]);

  const executive = me.executive;
  const exec = executive.name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
  const whatsappDigits = executive.whatsapp.replace(/\D/g, "");
  const typeLabel = me.client.document_type === "NIT" ? "Persona jurídica" : "Persona natural";

  return (
    <>
      <div className="hello">
        <small>¡Hola! 👋 {typeLabel}</small>
        <h1>{me.client.name}</h1>
      </div>

      {!contract ? (
        <div className="pcard"><Empty>No tienes contratos vigentes asociados a tu cuenta.</Empty></div>
      ) : (
        <div className="home-grid">
          <div className="pcard">
            <div className="exec">
              <span className="av">{exec || "CB"}</span>
              <div>
                <h3>{executive.name}</h3>
                <h4>Tu ejecutivo de servicio</h4>
                <p>Estamos aquí para ayudarte con cualquier duda que tengas sobre la administración de tu inmueble.</p>
              </div>
            </div>
            {(executive.email || whatsappDigits) && (
              <div className="contact">
                <span className="row">
                  <Icon name="mail" size={16} /> {executive.email}
                </span>
                {whatsappDigits && (
                  <a className="btn wa-btn" href={`https://wa.me/${whatsappDigits}`} target="_blank" rel="noopener noreferrer" aria-label="Escribir por WhatsApp">
                    <Icon name="whatsapp" size={22} />
                  </a>
                )}
              </div>
            )}
          </div>

          <Link href="/portal/documentos/certificados" className="pcard tile">
            <div>
              <span className="tico"><Icon name="certificate" size={30} /></span>
              <h3>Descargar certificados de retención</h3>
              {home && <div className="num">{home.document_counts.certificados} disponible(s)</div>}
            </div>
            <span className="icon-btn go"><Icon name="arrowUpRight" /></span>
          </Link>

          <Link href="/portal/documentos/facturas" className="pcard tile">
            <div>
              <span className="tico sage"><Icon name="receipt" size={30} /></span>
              <h3>Ver mis facturas</h3>
              {home && <div className="num">{home.document_counts.facturas} disponible(s)</div>}
            </div>
            <span className="icon-btn go"><Icon name="arrowUpRight" /></span>
          </Link>

          <div className="pcard cta-card">
            <h3>Gestionar mis requerimientos</h3>
            <p className="muted small" style={{ margin: 0 }}>
              {home ? `${home.open_requests} abierto(s)` : "Cargando…"} · solicitudes, quejas y sugerencias.
            </p>
            <div className="row">
              <Link href="/portal/requerimientos?crear=1" className="btn btn-sm">Crear requerimiento</Link>
              <Link href="/portal/requerimientos" className="btn btn-secondary btn-sm">Ver todos</Link>
            </div>
          </div>

          <div className="pcard span-2" style={{ gridRow: "span 2" }}>
            <h2 style={{ fontSize: "1.3rem" }}>Información de tu contrato</h2>
            <ErrorBox message={error} />
            <div className="contract-info">
              <div className="dates">
                <div><strong>Fecha inicio de contrato</strong><small>{formatDate(contract.start_date)}</small></div>
                <div><strong>Fecha fin de contrato</strong><small>{formatDate(contract.end_date)}</small></div>
              </div>
              <div className="pill-out">
                Estado: <b>{contract.status === "EN_RENOVACION" ? "En renovación" : "Activo"}</b>
              </div>
            </div>
            <dl className="dl" style={{ marginTop: "0.75rem" }}>
              <div><dt>Contrato</dt><dd>{contract.contract_number}</dd></div>
              <div><dt>Inmueble</dt><dd>{contract.property_address}</dd></div>
              {home && (
                <div>
                  <dt>Vigencia</dt>
                  <dd>
                    {home.days_remaining >= 0
                      ? `Faltan ${home.days_remaining} día(s) para el vencimiento.`
                      : `Venció hace ${Math.abs(home.days_remaining)} día(s).`}
                  </dd>
                </div>
              )}
            </dl>
            <div className="metric-bar">
              <span>Documentos en tu expediente digital:</span>
              <span className="val">{home ? home.total_documents : "—"}</span>
            </div>
          </div>

          <div className="pcard cta-card">
            <h3>Radica un documento en tu expediente</h3>
            <p className="muted small" style={{ margin: 0 }}>
              Pólizas, certificados y comunicaciones. Recibes tu número de radicado al instante.
            </p>
            <Link href="/portal/radicar" className="btn btn-sm" style={{ alignSelf: "flex-start" }}>
              <Icon name="upload" size={16} /> Radicar documento
            </Link>
          </div>
        </div>
      )}
    </>
  );
}
