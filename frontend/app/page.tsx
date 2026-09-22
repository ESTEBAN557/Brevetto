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
            <h3>Portal administrativo</h3>
            <p className="muted small">
              Bandeja de ingesta en tiempo real, validación en pantalla dividida, expedientes de contratos, alertas de
              vencimiento y auditoría global. Requiere usuario de Coltebienes.
            </p>
            <span className="option-cta">Ingresar →</span>
          </Link>
          <Link href="/portal/radicacion" className="option">
            <h3>Portal de radicación para inquilinos</h3>
            <p className="muted small">
              Radique pólizas, comunicaciones o facturas directamente en el expediente de su contrato y obtenga su
              comprobante oficial al instante.
            </p>
            <span className="option-cta">Radicar un documento →</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
