"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, FormEvent, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import { clearClientSession, getClientSession, getStoredContractId, storeContractId } from "@/lib/client-auth";
import { clientApi, clientAuthApi } from "@/lib/client-api";
import type { PortalContract, PortalMe } from "@/lib/client-types";
import { ErrorBox, Loading } from "../DataState";
import { Modal } from "../Modal";
import { Icon, IconName } from "./Icon";

interface PortalContextValue {
  me: PortalMe;
  contract: PortalContract | null;
  setContractId: (id: string) => void;
}

const PortalContext = createContext<PortalContextValue | null>(null);

export function usePortal(): PortalContextValue {
  const value = useContext(PortalContext);
  if (!value) throw new Error("usePortal debe usarse dentro de PortalShell");
  return value;
}

const DOCUMENT_LINKS = [
  { href: "/portal/documentos/estados-de-cuenta", label: "Estados de cuenta", color: "var(--gold)" },
  { href: "/portal/documentos/certificados", label: "Certificados", color: "var(--sage)" },
  { href: "/portal/documentos/facturas", label: "Facturas", color: "var(--stamp)" },
  { href: "/portal/documentos/contratos", label: "Contratos", color: "var(--terracotta)" },
];

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "CB"
  );
}

function NavLink({ href, icon, label, active }: { href: string; icon: IconName; label: string; active: boolean }) {
  return (
    <Link href={href} className={active ? "active" : undefined} title={label}>
      <span className="pico"><Icon name={icon} /></span>
      <span className="label">{label}</span>
    </Link>
  );
}

export function PortalShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<PortalMe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [contractId, setContractIdState] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [docsOpen, setDocsOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [passwordPrompt, setPasswordPrompt] = useState(false);

  useEffect(() => {
    if (!getClientSession()) {
      router.replace("/login");
      return;
    }
    clientApi
      .me()
      .then((data) => {
        setMe(data);
        const stored = getStoredContractId();
        const pick = data.contracts.find((c) => c.id === stored) ?? data.contracts[0];
        if (pick) setContractIdState(pick.id);
        if (!data.has_password && new URLSearchParams(window.location.search).get("crear-clave")) {
          setPasswordPrompt(true);
        }
      })
      .catch((err) => {
        if (!(err instanceof ApiError && err.status === 401)) {
          setError("No fue posible cargar tu información. Verifica la conexión con el servidor.");
        }
      });
  }, [router]);

  useEffect(() => {
    if (pathname.startsWith("/portal/documentos")) setDocsOpen(true);
    setMenuOpen(false);
  }, [pathname]);

  const setContractId = useCallback((id: string) => {
    setContractIdState(id);
    storeContractId(id);
  }, []);

  const value = useMemo<PortalContextValue | null>(
    () =>
      me
        ? { me, contract: me.contracts.find((c) => c.id === contractId) ?? null, setContractId }
        : null,
    [me, contractId, setContractId],
  );

  function logout() {
    clearClientSession();
    router.replace("/login");
  }

  if (error) {
    return (
      <div className="pcontent">
        <ErrorBox message={error} />
      </div>
    );
  }
  if (!value || !me) return <Loading label="Cargando tu portal…" />;

  const notifications = me.notifications;
  const contract = value.contract;
  const onDocs = pathname.startsWith("/portal/documentos");

  return (
    <PortalContext.Provider value={value}>
      <div className={`pshell${collapsed ? " collapsed" : ""}${menuOpen ? " menu-open" : ""}`}>
        <aside className="psidebar no-print">
          <button type="button" className="pcollapse" onClick={() => setCollapsed((v) => !v)} aria-label="Contraer menú">
            <Icon name="chevronLeft" size={16} />
          </button>
          <div className="plogo">
            <div className="brand-chip">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
            </div>
          </div>
          <nav className="pnav">
            <NavLink href="/portal" icon="home" label="Inicio" active={pathname === "/portal"} />
            <div>
              <button
                type="button"
                className={`pnav-btn${onDocs ? " active" : ""}`}
                onClick={() => setDocsOpen((v) => !v)}
                aria-expanded={docsOpen}
                title="Documentos"
              >
                <span className="pico"><Icon name="folder" /></span>
                <span className="label grow">Documentos</span>
                <span className={`chev${docsOpen ? " open" : ""}`}><Icon name="chevronDown" size={18} /></span>
              </button>
              {docsOpen && (
                <div className="psub">
                  {DOCUMENT_LINKS.map((link) => (
                    <Link key={link.href} href={link.href} className={pathname === link.href ? "active" : undefined}>
                      <span className="sq" style={{ background: link.color }} />
                      {link.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
            <NavLink href="/portal/radicar" icon="upload" label="Radicar documento" active={pathname === "/portal/radicar"} />
            <NavLink
              href="/portal/requerimientos"
              icon="tasks"
              label="Requerimientos"
              active={pathname.startsWith("/portal/requerimientos")}
            />
          </nav>
          <div className="psidebar-foot pnav">
            <button type="button" className="pnav-btn" onClick={logout} title="Cerrar sesión">
              <span className="pico"><Icon name="logout" /></span>
              <span className="label">Cerrar sesión</span>
            </button>
          </div>
        </aside>

        <div className="pmain">
          <header className="pheader no-print">
            <div className="row">
              <button type="button" className="pburger" onClick={() => setMenuOpen((v) => !v)} aria-label="Abrir menú">
                <Icon name="menu" />
              </button>
              <span className="ptitle">Portal de Autogestión</span>
            </div>
            <div className="pheader-right">
              <div className="pbell">
                <button type="button" onClick={() => setBellOpen((v) => !v)} aria-label="Notificaciones">
                  <Icon name="bell" />
                </button>
                <span className="count">{notifications.length}</span>
                {bellOpen && (
                  <div className="ppop">
                    <h4>Vencimientos documentales</h4>
                    {notifications.length === 0 && <span className="muted small">No tienes documentos por vencer.</span>}
                    {notifications.map((n, i) => (
                      <div key={i} className={`item${n.expired ? " expired" : ""}`}>
                        <strong>{n.document_type}</strong> · contrato {n.contract_number}
                        <br />
                        {n.expired ? "Venció el " : "Vence el "}
                        {n.expiration_date}
                      </div>
                    ))}
                    <Link href="/portal/radicar" className="btn btn-sm">Radicar documento actualizado</Link>
                  </div>
                )}
              </div>
              <div className="pchip">
                <span className="av">{initials(me.client.name)}</span>
                <span className="txt">
                  <strong className="truncate">{me.client.name}</strong>
                  {me.contracts.length > 0 ? (
                    <select
                      value={contract?.id ?? ""}
                      onChange={(e) => value.setContractId(e.target.value)}
                      aria-label="Contrato activo"
                    >
                      {me.contracts.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.contract_number} · {c.property_address}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className="muted">Sin contratos vigentes</span>
                  )}
                </span>
              </div>
            </div>
          </header>
          <div className="pcontent">{children}</div>
          <footer className="pfooter no-print">
            <span>Copyright © {new Date().getFullYear()} Coltebienes S.A.</span>
            <span>
              <a href="#">Política de privacidad</a> · <a href="#">Términos &amp; Condiciones</a>
            </span>
          </footer>
        </div>
      </div>
      {passwordPrompt && <CreatePasswordModal onClose={() => setPasswordPrompt(false)} />}
    </PortalContext.Provider>
  );
}

function CreatePasswordModal({ onClose }: { onClose: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await clientAuthApi.setPassword(password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No fue posible guardar la contraseña.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Crea tu contraseña" onClose={onClose} size="narrow">
      {done ? (
        <div className="stack">
          <div className="alert alert-success">
            Listo. La próxima vez podrás ingresar con tu correo y contraseña desde «Acceso clientes».
          </div>
          <div className="form-actions"><button type="button" onClick={onClose}>Continuar</button></div>
        </div>
      ) : (
        <form onSubmit={submit} className="stack">
          <p className="muted small">
            Es opcional: te permite ingresar con tu correo sin esperar un código. Mínimo 8 caracteres.
          </p>
          <label className="field">
            Nueva contraseña
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} autoComplete="new-password" required />
          </label>
          <label className="field">
            Confirmar contraseña
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} minLength={8} autoComplete="new-password" required />
          </label>
          <ErrorBox message={error} />
          <div className="form-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>Ahora no</button>
            <button type="submit" disabled={busy}>{busy && <span className="spinner" />} Guardar contraseña</button>
          </div>
        </form>
      )}
    </Modal>
  );
}
