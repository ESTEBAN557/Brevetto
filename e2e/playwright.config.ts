import { defineConfig, devices } from "@playwright/test";

/**
 * Pruebas de extremo a extremo de Brevetto (navegador real contra la aplicación levantada).
 *
 * Requieren un entorno con datos de demostración (`seed_demo_data` + `seed_client_portal_demo`) y el
 * eco del código de acceso activo (CLIENT_OTP_DEV_ECHO=True). NO ejecutar contra datos reales: algunas
 * pruebas crean mensajes y cambian estados de requerimientos.
 *
 *   BREVETTO_URL=https://localhost npm test          # stack de producción local (docker-compose.prod.yml)
 *   BREVETTO_URL=http://localhost:3000 npm test      # stack de desarrollo (docker-compose.yml)
 */
export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.BREVETTO_URL ?? "https://localhost",
    ignoreHTTPSErrors: true, // el stack local usa la CA interna de Caddy para "localhost"
    locale: "es-CO",
    timezoneId: "America/Bogota",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
});
