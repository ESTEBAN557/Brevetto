import { expect, test } from "@playwright/test";
import { loginClient, loginStaff } from "./helpers";

/* Flujos principales en el navegador: cada historia con un camino feliz y un flujo alternativo. */

test.describe("Acceso", () => {
  test("el personal entra al panel con usuario y contraseña", async ({ page }) => {
    await loginStaff(page);
    await expect(page.getByRole("link", { name: /Requerimientos/ })).toBeVisible();
  });

  test("credenciales incorrectas muestran un error y no dan acceso", async ({ page }) => {
    await page.goto("/login/empleados");
    await page.getByPlaceholder("Email o usuario").fill("demo");
    await page.getByPlaceholder("Contraseña").fill("clave-equivocada");
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.locator(".alert-error")).toBeVisible();
    await expect(page).toHaveURL(/\/login\/empleados/);
  });

  test("las rutas del panel exigen sesión", async ({ page }) => {
    await page.goto("/admin/requerimientos");
    await expect(page).toHaveURL(/\/login/);
  });

  test("el cliente entra a Mi Portal con código de verificación", async ({ page }) => {
    await loginClient(page);
    await expect(page.getByText("Información de tu contrato")).toBeVisible();
  });
});

test.describe("US-018 / US-022 · Buscar expedientes y filtrar por tipo", () => {
  test.beforeEach(async ({ page }) => loginStaff(page));

  test("buscar un contrato y abrir su expediente", async ({ page }) => {
    await page.goto("/admin/contracts");
    const firstRow = page.locator("table.table tbody tr").first();
    await expect(firstRow).toBeVisible();
    const number = (await firstRow.locator(".mono").first().textContent())?.trim() ?? "";
    await page.getByPlaceholder(/Buscar contrato/).fill(number);
    await page.keyboard.press("Enter");
    await expect(page.locator("table.table tbody tr")).toHaveCount(1);
    await page.locator("table.table tbody tr").first().getByRole("link").first().click();
    await expect(page.getByRole("heading", { name: new RegExp(number) })).toBeVisible();
  });

  test("una búsqueda sin coincidencias lo informa", async ({ page }) => {
    await page.goto("/admin/contracts");
    await page.getByPlaceholder(/Buscar contrato/).fill("CONT-9999-NO-EXISTE");
    await page.keyboard.press("Enter");
    await expect(page.getByText("No hay contratos que coincidan.")).toBeVisible();
  });

  test("filtrar el expediente por tipo y quitar el filtro", async ({ page }) => {
    await page.goto("/admin/contracts");
    await page.locator("table.table tbody tr").first().getByRole("link").first().click();
    const typeSelect = page.locator("#filter-type");
    await expect(typeSelect).toBeVisible();
    const options = await typeSelect.locator("option").allTextContents();
    test.skip(options.length < 2, "El expediente de demostración no tiene documentos tipificados");
    const total = await page.locator("section.card table.table tbody tr").count();
    await typeSelect.selectOption({ label: options[1] });
    const filtered = page.locator("section.card table.table tbody tr");
    await expect(filtered.first()).toContainText(options[1]);
    await page.getByRole("button", { name: "Quitar filtros" }).click();
    await expect(page.locator("section.card table.table tbody tr")).toHaveCount(total);
  });
});

test.describe("US-019 / US-021 · Ver e imprimir documentos", () => {
  test("la vista previa muestra el documento con las opciones de descarga e impresión", async ({ page }) => {
    await loginStaff(page);
    await page.goto("/admin/contracts");
    await page.locator("table.table tbody tr").first().getByRole("link").first().click();
    await page.getByRole("button", { name: "Vista previa" }).first().click();
    await expect(page.locator(".viewer iframe, .viewer img")).toBeVisible();
    await expect(page.getByRole("button", { name: /Imprimir/ })).toBeVisible();
    await expect(page.locator(".modal-footer").getByRole("button", { name: "Descargar" })).toBeVisible();
  });
});

test.describe("Requerimientos · atención por el personal", () => {
  test.beforeEach(async ({ page }) => loginStaff(page));

  test("responder a un cliente desde el panel", async ({ page }) => {
    await page.goto("/admin/requerimientos");
    await page.getByRole("tab", { name: /Todos/ }).click();
    await page.getByRole("link", { name: "Atender" }).first().click();
    await expect(page.getByRole("heading", { name: "Gestión del caso" })).toBeVisible();
    const closed = await page.getByText("ya no admite mensajes").isVisible();
    test.skip(closed, "El primer requerimiento de la demo está cerrado");
    const message = `Respuesta E2E ${Date.now()}`;
    await page.getByPlaceholder(/Escriba la respuesta/).fill(message);
    await page.getByRole("button", { name: "Enviar respuesta" }).click();
    await expect(page.locator(".chat").getByText(message)).toBeVisible();
  });

  test("no se puede resolver sin registrar la solución", async ({ page }) => {
    await page.goto("/admin/requerimientos");
    await page.getByRole("link", { name: "Atender" }).first().click();
    await expect(page.getByRole("heading", { name: "Gestión del caso" })).toBeVisible();
    const form = page.locator("form").filter({ has: page.getByText("Asesor asignado") });
    test.skip(!(await form.isVisible()), "No hay requerimientos abiertos en la demo");
    await form.getByRole("combobox").selectOption("RESUELTO");
    await form.getByPlaceholder(/Obligatoria/).fill("");
    await expect(page.getByText("escriba primero la solución")).toBeVisible();
    await expect(page.getByRole("button", { name: "Guardar cambios" })).toBeDisabled();
  });

  test("una búsqueda sin resultados lo indica", async ({ page }) => {
    await page.goto("/admin/requerimientos");
    await page.getByLabel("Buscar requerimientos").fill("zzz-sin-resultados");
    await page.getByRole("button", { name: "Buscar" }).click();
    await expect(page.getByText(/No hay requerimientos que coincidan/)).toBeVisible();
  });
});

test.describe("US-026 / US-027 · Radicación sin cuenta", () => {
  test("un contrato inexistente se rechaza con un mensaje", async ({ page }) => {
    await page.goto("/portal/radicacion");
    await page.getByPlaceholder("CONT-2026-042").fill("CONT-0000-404");
    await page.getByPlaceholder("900.123.456-1").fill("900.000.000-1");
    await page.getByRole("button", { name: "Validar" }).click();
    await expect(page.locator(".alert-error")).toContainText("No encontramos");
  });
});

test.describe("Manual de usuario", () => {
  test("es público y tiene las guías de clientes y personal", async ({ page }) => {
    await page.goto("/ayuda");
    await expect(page.getByRole("heading", { name: "Manual de usuario" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Clientes · Ingresar a Mi Portal/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Personal · Atender requerimientos/ })).toBeVisible();
    const sources = await page.evaluate(() => Array.from(document.images).map((img) => img.src));
    expect(sources.length).toBeGreaterThan(5);
    for (const src of sources) {
      const response = await page.request.get(src);
      expect(response.status(), src).toBe(200);
    }
  });
});
