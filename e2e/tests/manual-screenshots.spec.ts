import { expect, test } from "@playwright/test";
import path from "node:path";
import { loginStaff } from "./helpers";

/* Genera las capturas del manual de usuario (frontend/public/manual) desde la aplicación real.
   Ejecutar con datos de demostración:  npm run screenshots  */

const OUT = path.resolve(__dirname, "../../frontend/public/manual");
const shot = (name: string) => ({ path: path.join(OUT, name), type: "jpeg" as const, quality: 82 });

test.describe("@manual capturas del manual", () => {
  test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.25 });

  test("@manual expediente con filtro por tipo", async ({ page }) => {
    await loginStaff(page);
    // Se elige el expediente con más tipos documentales para que el filtro luzca en la captura.
    await page.goto("/admin/contracts");
    await expect(page.locator("table.table tbody tr").first()).toBeVisible();
    const links = await page.locator("table.table tbody tr a[href^='/admin/contracts/']").evaluateAll((els) =>
      els.map((el) => el.getAttribute("href") ?? ""),
    );
    let best = { href: links[0], types: 0 };
    for (const href of links.slice(0, 8)) {
      await page.goto(href);
      await expect(page.locator("#filter-type")).toBeVisible();
      const types = (await page.locator("#filter-type option").count()) - 1;
      if (types > best.types) best = { href, types };
    }
    await page.goto(best.href);
    const typeSelect = page.locator("#filter-type");
    await expect(typeSelect).toBeVisible();
    const options = await typeSelect.locator("option").allTextContents();
    if (options.length > 1) await typeSelect.selectOption({ label: options[1] });
    await page.waitForTimeout(400);
    await page.screenshot(shot("admin-expediente.jpg"));
  });

  test("@manual bandeja y atención de requerimientos", async ({ page }) => {
    await loginStaff(page);
    await page.goto("/admin/requerimientos");
    await page.getByRole("tab", { name: /Todos/ }).click();
    await expect(page.getByRole("link", { name: "Atender" }).first()).toBeVisible();
    await page.screenshot(shot("admin-requerimientos.jpg"));

    await page.getByRole("tab", { name: /Abiertos/ }).click();
    const open = page.getByRole("link", { name: "Atender" }).first();
    if (!(await open.isVisible().catch(() => false))) await page.getByRole("tab", { name: /Todos/ }).click();
    await page.getByRole("link", { name: "Atender" }).first().click();
    await expect(page.getByRole("heading", { name: "Gestión del caso" })).toBeVisible();
    await page.screenshot(shot("admin-requerimiento-detalle.jpg"));
  });
});
