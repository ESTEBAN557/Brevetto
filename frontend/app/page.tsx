import Link from "next/link";

export default function HomePage() {
  return (
    <main className="landing">
      <div className="card">
        <div className="brand-lockup">
          <div className="brand-chip">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
          </div>
          <div>
            <div className="kicker">Coltebienes S.A. · Sistema de Gestión Documental</div>
            <h1 style={{ margin: 0 }}>Brevetto</h1>
          </div>
        </div>
        <p className="muted">
          Radicación con número único, clasificación asistida por inteligencia artificial con validación humana y
          expedientes digitales con trazabilidad inmutable.
        </p>
        <div className="options">
          <Link href="/login" className="option">
            <h3>Mi Portal · clientes</h3>
            <p className="muted small">
              Ingresa con un código por mensaje de texto o correo para consultar estados de cuenta, facturas,
              certificados y contratos, radicar documentos y gestionar tus requerimientos.
            </p>
            <span className="option-cta">Ingresar →</span>
          </Link>
          <Link href="/login/empleados" className="option">
            <h3>Portal administrativo</h3>
            <p className="muted small">
              Bandeja de ingesta en tiempo real, validación en pantalla dividida, expedientes de contratos, alertas de
              vencimiento y auditoría global. Requiere usuario de Coltebienes.
            </p>
            <span className="option-cta">Acceso empleados →</span>
          </Link>
          <Link href="/portal/radicacion" className="option">
            <h3>Radicar sin cuenta</h3>
            <p className="muted small">
              Valida tu contrato con tu número de identificación y radica una póliza, comunicación o factura. Recibes
              tu comprobante oficial al instante.
            </p>
            <span className="option-cta">Radicar un documento →</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
