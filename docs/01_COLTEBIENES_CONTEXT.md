# Contexto de Negocio y Requerimientos de Coltebienes

## 1. Situación Actual en Coltebienes S.A.
Actualmente todos los documentos relacionados con un contrato de arrendamiento o venta de inmuebles y bodegas se administran de forma manual.

### El flujo operativo actual:
1. **Recepción:** Se reciben documentos físicos (cartas, solicitudes, comunicaciones, facturas, requerimientos de entidades, servicios públicos, etc.) o correos electrónicos.
2. **Impresión:** Los correos electrónicos que contienen información importante se imprimen para hacer parte física del expediente.
3. **Escaneo:** Todos estos documentos se escanean individualmente.
4. **Identificación manual:** La persona encargada revisa el papel escaneado e identifica manualmente a qué contrato o cliente pertenece.
5. **Apertura de carpeta:** Abre la carpeta en Windows / PDF y adiciona el documento al archivo digital del contrato.
6. **Archivo físico:** Finalmente, el documento físico se traslada a la bodega o estante de archivo.

### Impacto negativo del proceso manual:
- **Pérdida de tiempo:** ~40% del tiempo del personal administrativo se consume en radicación, escaneo y clasificación manual.
- **Riesgo de error:** 15% a 22% de margen de error al tipificar o asociar anexos a contratos equivocados.
- **Nula trazabilidad:** 0% de registro inmutable sobre quién vio o descargó un documento.
- **Dependencia de atención humana:** Los inquilinos deben llamar o enviar correos para conocer el estado de sus documentos o pólizas vencidas.

---

## 2. Objetivo de la Plataforma Brevetto
Desarrollar una plataforma inteligente de gestión documental que automatice la mayor cantidad posible de este proceso, facilitando tanto el ingreso como la consulta de la información mediante inteligencia artificial multimodal y arquitectura en la nube.

---

## 3. Las 6 Funcionalidades Esperadas por Coltebienes

### 1. Clasificación Automática de Documentos
- Escanear o subir múltiples documentos en un solo proceso.
- Identificar automáticamente a qué cliente o contrato pertenece cada documento utilizando OCR multimodal / IA (Google Gemini).
- Clasificar y almacenar cada documento en el expediente correspondiente sin intervención manual o con mínima validación (*Human-in-the-Loop*).

### 2. Gestión del Expediente Digital
- Cada contrato cuenta con un expediente electrónico único que consolida todos los documentos relacionados.
- Organización cronológica y agrupada por tipo documental (Legales, Pólizas, Facturación, Servicios Públicos, Comunicaciones).

### 3. Radicación de Documentos
- Generación automática de número de radicado consecutivo único (`RAD-YYYYMMDD-XXXXXX`).
- Registro inmutable de fecha, hora, usuario radicado, canal y checksum SHA-256.
- Admite tanto documentos físicos escaneados como archivos digitales nativos.

### 4. Radicación Web (Portal de Inquilinos)
- Portal web público accesible para clientes externos / arrendatarios.
- Carga directa de documentos (como renovación de pólizas) asociados a su contrato previa validación de credenciales (NIT/Cédula y N° Contrato).
- Generación de comprobante oficial de radicación digital para el cliente.

### 5. Consulta Documental
- Búsqueda ágil (< 2 segundos) por número de contrato, nombre de cliente, NIT, radicado o fecha.
- Visor integrado de documentos PDF / imágenes en la web sin descargar obligatoriamente.
- Descarga segura mediante URLs temporales prefirmadas.
- Impresión limpia del documento.
- Filtros por tipo documental y consulta del historial completo del expediente.

### 6. Trazabilidad y Auditoría
- Historial inmutable de todas las acciones sobre cada documento:
  - Quién lo cargó.
  - Cuándo fue recibido y radicado.
  - Modificaciones realizadas a sus metadatos.
  - Consultas y descargas efectuadas.
  - Versiones del documento cuando aplique.
