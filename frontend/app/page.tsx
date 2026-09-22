import Link from "next/link";

export default function HomePage() {
  return (
    <main className="landing">
      <div className="card">
        <h1>Brevetto</h1>
        <p className="muted">
          Sistema Inteligente de Gestión Documental de Coltebienes S.A. Radicación con número único,
          clasificación asistida por IA con validación humana y expedientes digitales auditables.
        </p>
        <div className="options">
          <Link href="/login" className="option">
            <h3>Portal administrativo</h3>
            <p className="muted small">
              Bandeja de ingesta en tiempo real, validación de documentos en pantalla dividida, expedientes de
              contratos e inspector de auditoría. Requiere usuario de Coltebienes.
            </p>
          </Link>
          <Link href="/portal/radicacion" className="option">
            <h3>Portal de radicación para inquilinos</h3>
            <p className="muted small">
              Radique pólizas, comunicaciones o facturas directamente en el expediente de su contrato y obtenga su
              comprobante oficial al instante.
            </p>
          </Link>
        </div>
      </div>
    </main>
  );
}
