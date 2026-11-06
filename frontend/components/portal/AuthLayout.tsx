import Link from "next/link";
import type { ReactNode } from "react";

/** Estructura común de las tres pantallas de acceso: formulario a la izquierda y panel visual a la derecha. */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="auth">
      <section className="auth-main">
        <div className="auth-box">
          <div className="auth-brand">
            <div className="brand-chip">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
            </div>
          </div>
          <div className="auth-title">
            <h1>Portal de Autogestión</h1>
            <p>¡Te damos la bienvenida!</p>
          </div>
          {children}
        </div>
      </section>
      <aside className="auth-hero" aria-hidden="true">
        <span className="eyebrow">Coltebienes S.A. · Brevetto</span>
        <h2>Tus contratos y documentos, siempre a la mano.</h2>
        <ul>
          <li>Descarga estados de cuenta, facturas y certificados cuando los necesites.</li>
          <li>Radica documentos en el expediente de tu contrato y recibe tu comprobante al instante.</li>
          <li>Haz seguimiento a tus requerimientos con trazabilidad completa.</li>
        </ul>
      </aside>
    </main>
  );
}

export function AuthLinks({ current }: { current: "quick" | "client" | "staff" }) {
  return (
    <>
      <div className="auth-links">
        {current !== "client" && <Link href="/login/clientes">Acceso clientes</Link>}
        {current === "client" && <Link href="/login">Ingreso con código</Link>}
        <span className="sep">·</span>
        {current !== "staff" ? <Link href="/login/empleados">Acceso empleados</Link> : <Link href="/login">Acceso clientes</Link>}
      </div>
      <div className="auth-foot">
        <Link href="/portal/radicacion" className="link-btn">
          Radicar un documento sin cuenta
        </Link>
      </div>
    </>
  );
}
