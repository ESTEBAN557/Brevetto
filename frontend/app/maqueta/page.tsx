import Link from "next/link";
import "./maqueta.css";

export const metadata = {
  title: "Maqueta · Coltebienes + Brevetto",
  description: "Copia visual de la home de Coltebienes.",
};

const PROPERTIES = [
  { tag: "Arriendo", kind: "LOCAL", title: "Local en arriendo – Guayabal, Medellín", loc: "Guayabal, Medellín", price: "$ 6.800.000", note: "/mes · Más IVA", tone: "" },
  { tag: "Venta", kind: "LOCAL", title: "Local en venta – Prado, Medellín", loc: "Prado, Medellín", price: "$ 1.250.000.000", note: "", tone: "b" },
  { tag: "Arriendo", kind: "OFICINA", title: "Oficina en arriendo – Ciudad del Río", loc: "Ciudad del Río, Medellín", price: "$ 4.200.000", note: "/mes · Más IVA", tone: "c" },
];

export default function MockupPage() {
  return (
    <div className="mq">
      <div className="mq-banner">
        <b>MAQUETA</b> · Copia visual de la home de Coltebienes. El menú «Acceso» y el pie son los puntos de unión con Brevetto.
        <Link href="/">Salir</Link>
      </div>

      <header className="mq-header">
        <div className="mq-wrap">
          <Link href="/maqueta" className="mq-logo" aria-label="Coltebienes">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/coltebienes-logo.png" alt="Coltebienes" />
          </Link>
          <nav className="mq-nav" aria-label="Principal">
            <a href="#">Inicio</a>
            <a href="#">Propiedades ▾</a>
            <a href="#">Servicios ▾</a>
            <a href="#">Nosotros ▾</a>
            <a href="#">Blog</a>
            <a href="#" className="pill">Contáctanos</a>
          </nav>
          <div className="mq-tools">
            <span className="mq-round pse" title="Pagos PSE">pse</span>
            <span className="mq-round wa" title="WhatsApp">WA</span>
            <Link href="/login" className="mq-portal-btn">Mi Portal</Link>
            <button type="button" className="mq-access" aria-haspopup="true">👤 Acceso ▾</button>
            <div className="mq-menu" role="menu">
              <Link href="/login" role="menuitem">
                <strong>Soy cliente · Mi Portal</strong>
                <small>Consulta tus documentos y requerimientos</small>
              </Link>
              <Link href="/portal/radicacion" role="menuitem">
                <strong>Radicar un documento</strong>
                <small>Sin cuenta, con tu número de contrato</small>
              </Link>
              <Link href="/login/empleados" role="menuitem">
                <strong>Soy empleado de Coltebienes</strong>
                <small>Portal administrativo</small>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <section className="mq-hero">
        <span className="mq-chip">Bodegas · Locales · Oficinas · Lotes</span>
        <h1>
          <em>45</em> años de trayectoria industrial en Antioquia
        </h1>
        <p className="sub">Encuentra el espacio ideal para tu negocio</p>
        <div className="mq-search" aria-label="Buscador (maqueta)">
          <div className="grid4">
            <div className="cell"><label>Tipo</label><div className="val">Todos los tipos</div></div>
            <div className="cell"><label>Operación</label><div className="val">Arriendo o venta</div></div>
            <div className="cell"><label>Ciudad</label><div className="val">Todas las ciudades</div></div>
            <div className="cell"><label>Zona</label><div className="val dim">Todas las zonas</div></div>
          </div>
          <div className="row2">
            <div className="cell"><label>Precio</label><div className="val dim">Desde — Hasta</div></div>
            <div className="cell"><label>Área en m²</label><div className="val dim">Desde — Hasta</div></div>
          </div>
          <div className="row3">
            <div className="cell"><label>Código</label><div className="val dim">495-40761</div></div>
            <div className="cell"><label>¿Qué estás buscando?</label><div className="val dim">Ej: bodega con muelle en Guarne…</div></div>
            <div className="go">Buscar</div>
          </div>
        </div>
        <div className="mq-popular">
          <span>Popular:</span><span>Bodegas en arriendo</span><span>Locales en venta</span><span>Oficinas Laureles</span><span>El Poblado</span><span>Guayabal</span>
        </div>
      </section>

      <section className="mq-stats">
        <div className="mq-wrap">
          <div><strong>529+</strong><span>Propiedades activas</span></div>
          <div><strong>45+</strong><span>Años de experiencia</span></div>
          <div><strong>100%</strong><span>Enfoque comercial</span></div>
        </div>
      </section>

      <section className="mq-explore">
        <div className="mq-wrap">
          <small>EXPLORAR:</small>
          {["Locales comerciales", "Oficinas en Medellín", "Bodegas en Antioquia", "Bodegas en Itagüí", "Bodegas en Sabaneta", "Bodegas en Bello", "Bodegas en Rionegro", "Bodegas en Guarne"].map((t) => (
            <span key={t} className="mq-tag">{t}</span>
          ))}
        </div>
      </section>

      <section className="mq-section">
        <div className="mq-wrap">
          <div className="mq-title">
            <h2>Propiedades destacadas</h2>
            <p>Inmuebles selectos</p>
            <i />
          </div>
          <div className="mq-cards">
            {PROPERTIES.map((p) => (
              <article key={p.title} className="mq-card">
                <div className={`mq-photo ${p.tone}`}>
                  <span className="mq-badge l">★ Destacado</span>
                  <span className="mq-badge r">{p.tag}</span>
                  foto
                </div>
                <div className="body">
                  <span className="kind">{p.kind}</span>
                  <h3>{p.title}</h3>
                  <div className="loc">📍 {p.loc}</div>
                  <div className="price">{p.price} <small>{p.note}</small></div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mq-section">
        <div className="mq-wrap">
          <div className="mq-title">
            <h2>¿Por qué Coltebienes?</h2>
            <i />
          </div>
          <div className="mq-why">
            <div><span className="n">01</span><h3>Experiencia industrial</h3><p>45 años acompañando a empresas que buscan bodegas, locales y oficinas en Antioquia.</p></div>
            <div><span className="n">02</span><h3>Gestión transparente</h3><p>Tus documentos y su trazabilidad disponibles cuando los necesites, con registro de cada consulta.</p></div>
            <div><span className="n">03</span><h3>Atención cercana</h3><p>Un ejecutivo de servicio y un asistente virtual para resolver tus dudas.</p></div>
          </div>
        </div>
      </section>

      <section className="mq-cta">
        <h2>Encuentra el espacio ideal para tu empresa</h2>
        <p>Asesoría especializada en bodegas, locales y oficinas.</p>
        <a href="#" className="btn">Habla con un asesor</a>
      </section>

      <footer className="mq-footer">
        <div className="mq-wrap">
          <div>
            <h4>Coltebienes S.A.</h4>
            <p>Los especialistas en bodegas y locales. NIT de ejemplo 000.000.000-0.</p>
          </div>
          <div><h4>Propiedades</h4><a href="#">Bodegas</a><a href="#">Locales</a><a href="#">Oficinas</a><a href="#">Lotes</a></div>
          <div><h4>Clientes</h4><Link href="/login">Mi Portal</Link><Link href="/portal/radicacion">Radicar documento</Link><a href="#">Pagos PSE</a></div>
          <div><h4>Legal</h4><a href="#">Aviso de privacidad</a><a href="#">Política de datos</a><a href="#">Política de cookies</a></div>
        </div>
        <div className="mq-copy">© {new Date().getFullYear()} Coltebienes S.A. · Maqueta</div>
      </footer>

      <div className="mq-bot" aria-hidden="true">
        <div className="bubble">¡Hola! Soy Colte, ¿en qué te ayudo?<small>Asistente virtual · Coltebienes</small></div>
        <div className="face">🤖</div>
      </div>
    </div>
  );
}
