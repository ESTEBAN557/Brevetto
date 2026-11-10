import { expect, type Page } from "@playwright/test";

// Credenciales de los datos de demostración (`manage.py seed_demo_data`), sobreescribibles por entorno.
export const STAFF_USER = process.env.E2E_STAFF_USER ?? "demo";
export const STAFF_PASSWORD = process.env.E2E_STAFF_PASSWORD ?? "Brevetto2026!";
// Cliente de `manage.py seed_client_portal_demo`.
export const CLIENT_NIT = process.env.E2E_CLIENT_NIT ?? "900.845.112-3";

export async function loginStaff(page: Page) {
  await page.goto("/login/empleados");
  await page.getByPlaceholder("Email o usuario").fill(STAFF_USER);
  await page.getByPlaceholder("Contraseña").fill(STAFF_PASSWORD);
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

/** Ingreso de cliente con código de un solo uso; requiere CLIENT_OTP_DEV_ECHO=True (el código se muestra). */
export async function loginClient(page: Page) {
  await page.goto("/login");
  await page.getByPlaceholder("Número de documento").fill(CLIENT_NIT);
  await page.getByLabel("Correo electrónico").check();
  await page.getByRole("button", { name: "Continuar" }).click();
  const hint = page.locator(".dev-hint strong");
  await expect(hint).toBeVisible();
  const code = (await hint.textContent())?.trim() ?? "";
  expect(code).toMatch(/^\d{6}$/);
  // Pegar el código completo en la primera casilla: la pantalla lo verifica automáticamente.
  await page.getByLabel("Dígito 1").fill(code);
  await expect(page).toHaveURL(/\/portal/);
  // Primer ingreso: el portal ofrece crear contraseña; se descarta si aparece.
  const later = page.getByRole("button", { name: "Ahora no" });
  if (await later.isVisible().catch(() => false)) await later.click();
}
