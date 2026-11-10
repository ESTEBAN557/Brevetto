import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Manual de usuario · Brevetto",
  description: "Guía paso a paso de Brevetto para clientes y personal de Coltebienes.",
};

/* Manual de usuario integrado en la aplicación (entregable del Sprint 3).
   Página pública y estática: se puede abrir sin iniciar sesión e imprimir con Ctrl+P. */

function Shot({ src, alt, caption }: { src: string; alt: string; caption: string }) {
  return (
    <figure>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={`/manual/${src}`} alt={alt} loading="lazy" />
      <figcaption>{caption}</figcaption>
    </figure>
  );
}

function Steps({ children }: { children: ReactNode }) {
  return <ol className="steps-list">{children}</ol>;
}

function Tip({ children }: { children: ReactNode }) {
  return <p className="tip">{children}</p>;
}

function Warn({ children }: { children: ReactNode }) {
  return <p className="warn">{children}</p>;
}

const TOC: { group: string; items: [string, string][] }[] = [
  { group: "Empezar", items: [["inicio", "Qué es Brevetto"], ["acceso", "Cómo entrar"]] },
  {
    group: "Clientes",
    items: [
      ["c-ingreso", "Ingresar a Mi Portal"],
      ["c-inicio", "Mi contrato y vencimientos"],
      ["c-documentos", "Descargar documentos"],
      ["c-radicar", "Radicar un documento"],
      ["c-requerimientos", "Requerimientos"],
    ],
  },
  {
    group: "Personal Coltebienes",
    items: [
      ["personal", "Ingresar al panel"],
      ["p-panel", "Panel de control"],
      ["p-radicar", "Radicar documentos"],
      ["p-validar", "Validar la clasificación"],
      ["p-expedientes", "Buscar y consultar expedientes"],
      ["p-requerimientos", "Atender requerimientos"],
      ["p-auditoria", "Auditoría"],
    ],
  },
  { group: "Referencia", items: [["glosario", "Glosario"], ["faq", "Preguntas frecuentes"]] },
];

export default function ManualPage() {
  return (
    <main className="page" style={{ maxWidth: 1180 }}>
      <div className="page-header no-print">
        <div className="brand-lockup" style={{ marginBottom: 0 }}>
          <span className="brand-chip">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
          </span>
          <span>
            <span className="kicker">Brevetto · Coltebienes S.A.</span>
            <h1 style={{ margin: 0 }}>Manual de usuario</h1>
          </span>
        </div>
        <Link href="/" className="btn btn-secondary">
          ← Ir a Brevetto
        </Link>
      </div>

      <div className="manual">
        <nav className="manual-toc" aria-label="Contenido del manual">
          {TOC.map((group) => (
            <div key={group.group} style={{ display: "contents" }}>
              <span className="toc-group">{group.group}</span>
              {group.items.map(([id, label]) => (
                <a key={id} href={`#${id}`}>
                  {label}
                </a>
              ))}
            </div>
          ))}
        </nav>

        <article>
          {/* ------------------------------------------------------------ inicio */}
          <section id="inicio">
            <h2>¿Qué es Brevetto?</h2>
            <p>
              Brevetto es el sistema de gestión documental de Coltebienes. Reúne en un solo lugar los documentos de cada
              contrato de arrendamiento (pólizas, facturas, certificados, RUT, cartas, actas) en un <strong>expediente
              digital</strong>, les asigna un número de <strong>radicado</strong> único y deja registro de quién los
              consultó, descargó o modificó.
            </p>
            <p>Cuando llega un documento, Brevetto lo procesa así:</p>
            <div className="flow" aria-label="Recorrido de un documento">
              <span>1. Llega el documento</span>
              <i>→</i>
              <span>2. Se radica (RAD-AAAAMMDD-000001)</span>
              <i>→</i>
              <span>3. La IA lo lee y lo clasifica</span>
              <i>→</i>
              <span>4. Si hay duda, lo revisa una persona</span>
              <i>→</i>
              <span>5. Se archiva en el expediente</span>
            </div>
            <div className="manual-audience">
              <a className="option" href="#c-ingreso">
                <h3>Soy cliente (arrendatario)</h3>
                <p className="small muted">
                  Consultar mi contrato, descargar estados de cuenta y facturas, enviar documentos y hacer solicitudes.
                </p>
                <span className="option-cta">Ver guía para clientes →</span>
              </a>
              <a className="option" href="#personal">
                <h3>Soy empleado de Coltebienes</h3>
                <p className="small muted">
                  Radicar, validar la clasificación, consultar expedientes, atender requerimientos y revisar la auditoría.
                </p>
                <span className="option-cta">Ver guía para el personal →</span>
              </a>
            </div>
          </section>

          <section id="acceso">
            <h2>Cómo entrar</h2>
            <p>
              Brevetto funciona en el navegador (Chrome, Edge, Firefox o Safari actualizados), en computador o celular. No
              hay que instalar nada. En la página de inicio hay tres puertas:
            </p>
            <table className="table">
              <thead>
                <tr>
                  <th>Opción</th>
                  <th>Para quién</th>
                  <th>Qué necesita</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <strong>Mi Portal · clientes</strong>
                  </td>
                  <td>Arrendatarios con contrato vigente</td>
                  <td>Tipo y número de documento (NIT o cédula) registrados en Coltebienes</td>
                </tr>
                <tr>
                  <td>
                    <strong>Portal administrativo</strong>
                  </td>
                  <td>Personal de Coltebienes</td>
                  <td>Usuario o correo y contraseña entregados por el administrador</td>
                </tr>
                <tr>
                  <td>
                    <strong>Radicar sin cuenta</strong>
                  </td>
                  <td>Cualquier arrendatario o tercero</td>
                  <td>Número de contrato y NIT o cédula del titular</td>
                </tr>
              </tbody>
            </table>
          </section>

          {/* ---------------------------------------------------------- clientes */}
          <section id="c-ingreso">
            <h2>Clientes · Ingresar a Mi Portal</h2>
            <Steps>
              <li>
                En la página de inicio elija <strong>Mi Portal · clientes</strong>.
              </li>
              <li>Seleccione el tipo de documento (NIT, cédula…) y escriba el número, con o sin puntos y guion.</li>
              <li>
                Elija cómo quiere recibir el código: <strong>mensaje de texto</strong> o <strong>correo electrónico</strong>, y
                pulse <strong>Continuar</strong>.
              </li>
              <li>Escriba el código de 6 dígitos que recibió. Vence a los 10 minutos.</li>
              <li>
                La primera vez, Brevetto le ofrece crear una contraseña. Si la crea, la próxima vez puede entrar por{" "}
                <strong>Acceso clientes</strong> con su correo y contraseña.
              </li>
            </Steps>
            <Shot src="login.jpg" alt="Pantalla de ingreso de clientes" caption="Ingreso con documento y código de verificación." />
            <Tip>
              Por seguridad, la pantalla no dice si un documento está o no registrado. Si no le llega el código, revise que
              su correo y celular estén actualizados con Coltebienes. Puede pedir un código nuevo después de 45 segundos;
              tras 5 intentos fallidos el código se bloquea.
            </Tip>
          </section>

          <section id="c-inicio">
            <h2>Clientes · Mi contrato y vencimientos</h2>
            <p>
              Al entrar ve su contrato: inmueble, fechas de inicio y fin, días que faltan para el vencimiento y cuántos
              documentos tiene en su expediente. Si tiene varios contratos, cámbielos desde el selector del encabezado.
            </p>
            <p>
              La <strong>campana</strong> muestra las pólizas o documentos próximos a vencer. Desde allí, el botón{" "}
              <strong>Radicar documento actualizado</strong> lo lleva directo a enviar la renovación.
            </p>
            <Shot src="portal-inicio.jpg" alt="Inicio de Mi Portal" caption="Inicio de Mi Portal: contrato, accesos rápidos y ejecutivo de servicio." />
          </section>

          <section id="c-documentos">
            <h2>Clientes · Descargar documentos</h2>
            <Steps>
              <li>
                En el menú <strong>Documentos</strong> elija <strong>Estados de cuenta</strong>, <strong>Facturas</strong>,{" "}
                <strong>Certificados</strong> o <strong>Contratos</strong>.
              </li>
              <li>Filtre por año, mes o número de radicado si lo necesita.</li>
              <li>
                Pulse el ícono de <strong>descarga</strong>. El archivo se abre en una pestaña nueva; el enlace es temporal y
                vence a los 15 minutos.
              </li>
            </Steps>
            <Shot src="portal-estados.jpg" alt="Estados de cuenta" caption="Estados de cuenta agrupados por año y mes." />
            <Tip>Solo verá los documentos de sus propios contratos. Cada descarga queda registrada por seguridad.</Tip>
          </section>

          <section id="c-radicar">
            <h2>Clientes · Radicar un documento</h2>
            <p>
              <strong>Con cuenta:</strong> en Mi Portal pulse <strong>Radicar documento</strong>, elija el contrato, el tipo de
              documento (por ejemplo, Póliza de cumplimiento) y el archivo. Si el tipo vence, indique la fecha de
              vencimiento.
            </p>
            <p>
              <strong>Sin cuenta:</strong> en la página de inicio elija <strong>Radicar sin cuenta</strong> y siga los 3 pasos:
            </p>
            <Steps>
              <li>
                <strong>Validar contrato:</strong> escriba el número de contrato (ej. CONT-2026-042) y el NIT o cédula del
                titular.
              </li>
              <li>
                <strong>Cargar documento:</strong> elija el tipo, escriba su nombre y adjunte el archivo PDF, JPG o PNG (máximo
                25 MB).
              </li>
              <li>
                <strong>Comprobante:</strong> reciba el número de radicado. Puede previsualizarlo e imprimirlo; incluye un
                código QR y una huella digital del archivo.
              </li>
            </Steps>
            <Shot src="radicacion.jpg" alt="Radicación sin cuenta" caption="Radicación sin cuenta: paso 1, validar el contrato." />
            <Warn>
              Si el contrato o el documento de identidad no coinciden, Brevetto no recibe el archivo. Revise los datos o
              comuníquese con Coltebienes. Se rechazan archivos de otros formatos o de más de 25 MB.
            </Warn>
          </section>

          <section id="c-requerimientos">
            <h2>Clientes · Requerimientos (solicitudes, quejas y sugerencias)</h2>
            <Steps>
              <li>
                Vaya a <strong>Requerimientos</strong> y pulse <strong>Crear requerimiento</strong>.
              </li>
              <li>
                En <strong>¿Qué necesitas reportar?</strong> elija el caso (por ejemplo, Renovación del contrato o Reparaciones
                locativas), escriba el asunto y la descripción y, si quiere, adjunte archivos de hasta 10 MB.
              </li>
              <li>
                Siga el avance en la línea de estados: <em>Nuevo → Asignado → En proceso → Resuelto → Cerrado</em>.
              </li>
              <li>
                En <strong>Chat</strong> converse con su asesor; en <strong>Adjuntos</strong> agregue archivos. Recibirá un
                correo cada vez que Coltebienes responda o cambie el estado.
              </li>
            </Steps>
            <Shot src="portal-req-lista.jpg" alt="Lista de requerimientos" caption="Lista de requerimientos con su estado y asesor." />
            <Shot src="portal-req-detalle.jpg" alt="Detalle de un requerimiento" caption="Detalle: línea de estados, datos del caso y solución." />
            <Shot src="portal-req-chat.jpg" alt="Chat del requerimiento" caption="Chat con el asesor de Coltebienes." />
            <Tip>Un requerimiento cerrado ya no admite mensajes ni archivos. Si necesita algo más, cree uno nuevo.</Tip>
          </section>

          {/* ---------------------------------------------------------- personal */}
          <section id="personal">
            <h2>Personal · Ingresar al panel</h2>
            <Steps>
              <li>
                En la página de inicio elija <strong>Portal administrativo</strong> (o vaya a <em>Acceso empleados</em>).
              </li>
              <li>Escriba su usuario o correo y su contraseña.</li>
              <li>
                El menú de la izquierda lleva a cada módulo. Para salir, use <strong>Cerrar sesión</strong> al final del menú.
              </li>
            </Steps>
            <Tip>La sesión dura 8 horas. Las cuentas del personal las crea el administrador del sistema.</Tip>
          </section>

          <section id="p-panel">
            <h2>Personal · Panel de control</h2>
            <p>La pantalla principal muestra, de arriba hacia abajo:</p>
            <ul>
              <li>
                <strong>Indicadores:</strong> porcentaje de documentos clasificados sin intervención, acierto de la IA, tiempo
                promedio de clasificación, horas ahorradas, pendientes y alertas. Cambie el periodo con el selector.
              </li>
              <li>
                <strong>Vencimientos:</strong> documentos vencidos o por vencer en 30 días, con los datos de contacto del
                arrendatario para gestionar la renovación.
              </li>
              <li>
                <strong>Bandeja de ingesta:</strong> todos los documentos radicados, que se actualiza sola cada 5 segundos.
                Busque por radicado, archivo, contrato o cliente y filtre por estado, canal, tipo o fechas.
              </li>
            </ul>
            <Shot src="admin-inicio.jpg" alt="Panel de control" caption="Panel de control con indicadores y bandeja de ingesta." />
            <table className="table">
              <thead>
                <tr>
                  <th>Estado del documento</th>
                  <th>Qué significa</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <span className="badge badge-RECIBIDO">Recibido</span>
                  </td>
                  <td>Radicado; espera el análisis de la IA.</td>
                </tr>
                <tr>
                  <td>
                    <span className="badge badge-PROCESANDO">Procesando</span>
                  </td>
                  <td>La IA lo está leyendo (normalmente menos de un minuto).</td>
                </tr>
                <tr>
                  <td>
                    <span className="badge badge-REQUIERE_REVISION">Requiere revisión</span>
                  </td>
                  <td>La IA no tuvo suficiente confianza o no identificó el contrato: lo debe validar una persona.</td>
                </tr>
                <tr>
                  <td>
                    <span className="badge badge-PROCESADO">Procesado</span>
                  </td>
                  <td>Clasificado y archivado en su expediente.</td>
                </tr>
                <tr>
                  <td>
                    <span className="badge badge-FALLIDO">Fallido</span>
                  </td>
                  <td>No se pudo procesar tras varios intentos; revíselo manualmente.</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section id="p-radicar">
            <h2>Personal · Radicar documentos</h2>
            <Steps>
              <li>
                En el menú elija <strong>Radicar documentos</strong>.
              </li>
              <li>
                Indique el canal: <em>Documento físico escaneado</em>, <em>Digital cargado por personal</em> o{" "}
                <em>Recibido por correo electrónico</em>.
              </li>
              <li>Si conoce el contrato, búsquelo: el documento se archiva directamente en ese expediente.</li>
              <li>
                Arrastre uno o varios archivos (PDF, JPG o PNG, hasta 25 MB cada uno) y pulse <strong>Radicar</strong>.
              </li>
              <li>
                Cada archivo recibe su radicado al instante. La IA lo analiza en segundo plano; puede seguir trabajando.
              </li>
            </Steps>
          </section>

          <section id="p-validar">
            <h2>Personal · Validar la clasificación (revisión humana)</h2>
            <p>
              Cuando la IA tiene menos de 85 % de confianza, no encuentra el contrato o encuentra varios posibles, el
              documento llega a <strong>Validación HITL</strong>. Nada se archiva sin control.
            </p>
            <Steps>
              <li>
                Abra <strong>Validación HITL</strong>. Cada fila muestra la sugerencia, la confianza y el motivo.
              </li>
              <li>
                Pulse <strong>Revisar</strong>: a la izquierda ve el documento y a la derecha las sugerencias de la IA.
              </li>
              <li>Confirme o corrija el contrato, el tipo de documento y las fechas. Para pólizas, el vencimiento es obligatorio.</li>
              <li>
                Pulse <strong>Confirmar clasificación</strong>. El documento pasa a Procesado y su decisión queda en la
                auditoría.
              </li>
            </Steps>
            <Shot src="admin-revision.jpg" alt="Bandeja de validación" caption="Bandeja de validación humana con la sugerencia y la confianza de la IA." />
          </section>

          <section id="p-expedientes">
            <h2>Personal · Buscar y consultar expedientes</h2>
            <Steps>
              <li>
                Abra <strong>Contratos y expedientes</strong> y busque por número de contrato, razón social, NIT o cédula,
                correo o dirección del inmueble. Si nada coincide, la pantalla lo indica.
              </li>
              <li>Abra el contrato. Los documentos aparecen agrupados por categoría.</li>
              <li>
                Use <strong>Tipo de documento</strong> o <strong>Categoría</strong> para filtrar (por ejemplo, solo pólizas) y{" "}
                <strong>Quitar filtros</strong> para volver a ver todo.
              </li>
              <li>
                <strong>Vista previa</strong> abre el documento sin descargarlo. Desde allí puede <strong>Descargar</strong> o{" "}
                <strong>Imprimir</strong>. Consultar, descargar o imprimir nunca modifica el original.
              </li>
              <li>
                <strong>Descargar Expediente (.ZIP)</strong> baja todos los documentos y un índice con la huella de cada
                archivo, útil para auditorías externas.
              </li>
              <li>
                La pestaña <strong>Bitácora del Expediente</strong> muestra quién hizo qué sobre cualquier documento del
                contrato.
              </li>
            </Steps>
            <Shot src="admin-contratos.jpg" alt="Contratos y expedientes" caption="Búsqueda de contratos con filtros por estado y fechas." />
            <Shot src="admin-expediente.jpg" alt="Expediente con filtro por tipo" caption="Expediente de un contrato con el filtro por tipo de documento." />
            <Warn>
              Si un archivo no está disponible en el repositorio, Brevetto lo indica con un mensaje y no registra la consulta.
              Informe al administrador del sistema.
            </Warn>
          </section>

          <section id="p-requerimientos">
            <h2>Personal · Atender requerimientos</h2>
            <Steps>
              <li>
                Abra <strong>Requerimientos</strong>. El número junto al menú indica los casos abiertos.
              </li>
              <li>Filtre por estado (Abiertos, Nuevos, En proceso…) o busque por número, asunto, cliente, NIT o contrato.</li>
              <li>
                Pulse <strong>Atender</strong>. Verá lo que reporta el cliente, sus datos de contacto y el contrato.
              </li>
              <li>
                En <strong>Gestión del caso</strong> asigne un asesor (el caso pasa a Asignado), cambie el estado y agregue una
                nota de seguimiento.
              </li>
              <li>Responda en la conversación y adjunte archivos si hace falta.</li>
              <li>
                Para marcar el caso como <strong>Resuelto</strong> o <strong>Cerrado</strong> escriba primero la solución.
              </li>
            </Steps>
            <Shot src="admin-requerimientos.jpg" alt="Bandeja de requerimientos" caption="Bandeja de requerimientos del personal." />
            <Shot src="admin-requerimiento-detalle.jpg" alt="Atención de un requerimiento" caption="Atención de un requerimiento: conversación, adjuntos, gestión y seguimiento." />
            <Tip>
              Cada respuesta y cada cambio de estado le llega al cliente por correo y lo ve en Mi Portal. Un caso cerrado ya
              no se puede modificar.
            </Tip>
          </section>

          <section id="p-auditoria">
            <h2>Personal · Auditoría</h2>
            <p>
              <strong>Auditoría global</strong> responde quién hizo qué y cuándo: cargas, clasificaciones de la IA,
              validaciones, ediciones de metadatos, consultas, descargas y alertas de vencimiento.
            </p>
            <Steps>
              <li>Filtre por acción, usuario (o «sistema» para la IA), rango de fechas, radicado, contrato o dirección IP.</li>
              <li>Pulse un evento para ver el detalle completo, por ejemplo el valor anterior y el nuevo de una edición.</li>
            </Steps>
            <Shot src="admin-auditoria.jpg" alt="Auditoría global" caption="Auditoría global con filtros y sello de registro inmutable." />
            <Tip>
              Los registros de auditoría no se pueden modificar ni borrar, ni desde la aplicación ni directamente en la base de
              datos.
            </Tip>
          </section>

          {/* -------------------------------------------------------- referencia */}
          <section id="glosario">
            <h2>Glosario</h2>
            <table className="table">
              <tbody>
                <tr>
                  <td>
                    <strong>Radicado</strong>
                  </td>
                  <td>Número único de recepción con el formato RAD-AAAAMMDD-000001. Nunca se repite.</td>
                </tr>
                <tr>
                  <td>
                    <strong>Expediente digital</strong>
                  </td>
                  <td>Carpeta con todos los documentos de un contrato.</td>
                </tr>
                <tr>
                  <td>
                    <strong>Confianza</strong>
                  </td>
                  <td>Qué tan segura está la IA de su clasificación (0 a 100 %). Por debajo de 85 % decide una persona.</td>
                </tr>
                <tr>
                  <td>
                    <strong>HITL</strong>
                  </td>
                  <td>«Human in the loop»: revisión humana de lo que la IA no puede decidir sola.</td>
                </tr>
                <tr>
                  <td>
                    <strong>Requerimiento</strong>
                  </td>
                  <td>Solicitud, queja o sugerencia de un cliente, con seguimiento por estados.</td>
                </tr>
                <tr>
                  <td>
                    <strong>Bitácora / auditoría</strong>
                  </td>
                  <td>Registro inalterable de cada acción sobre los documentos.</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section id="faq">
            <h2>Preguntas frecuentes</h2>
            <dl className="suggestion" style={{ gridTemplateColumns: "1fr", gap: "0.2rem 0" }}>
              <dt>
                <strong>No me llega el código de acceso.</strong>
              </dt>
              <dd>
                Espere 45 segundos y pida otro, o cambie a correo electrónico. Si sigue sin llegar, sus datos de contacto pueden
                estar desactualizados: comuníquese con Coltebienes.
              </dd>
              <dt style={{ marginTop: "0.75rem" }}>
                <strong>El documento no se ve en la vista previa.</strong>
              </dt>
              <dd>
                El acceso vence a los 15 minutos: pulse <em>Renovar acceso</em>. También puede abrirlo en otra pestaña o
                descargarlo.
              </dd>
              <dt style={{ marginTop: "0.75rem" }}>
                <strong>Un documento lleva mucho tiempo en «Procesando».</strong>
              </dt>
              <dd>
                Brevetto lo reintenta solo cada 5 minutos. Si la IA no está disponible, el documento pasa a revisión humana.
              </dd>
              <dt style={{ marginTop: "0.75rem" }}>
                <strong>¿Se puede borrar un documento o un registro de auditoría?</strong>
              </dt>
              <dd>No. Para corregir un error se editan los metadatos, y el cambio queda registrado con su valor anterior.</dd>
              <dt style={{ marginTop: "0.75rem" }}>
                <strong>¿Cómo imprimo este manual?</strong>
              </dt>
              <dd>Use Ctrl+P (Cmd+P en Mac). El índice lateral no se imprime.</dd>
            </dl>
          </section>
        </article>
      </div>
    </main>
  );
}
