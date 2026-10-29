import { expect, test, type Page } from "@playwright/test";
import { MockApi } from "./mock-api";

const routes = [
  "/",
  "/library",
  "/explore",
  "/settings",
  "/help",
  "/p/p1",
  "/p/p1/context",
  "/m/m1",
  "/shared/s1",
  "/nowhere",
];

// Known: the legacy context files table, which package D replaces with the Sources sheet.
const sizes = [
  { width: 390, height: 844, legacy: ["/p/p1/context"] },
  { width: 1440, height: 900, legacy: [] },
];

const overflow = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

for (const size of sizes)
  test(`no route scrolls sideways at ${size.width} px`, async ({ page }, info) => {
    const api = new MockApi();
    api.seed();
    api.shares.set("s1", 1);
    await api.install(page);
    await page.setViewportSize({ width: size.width, height: size.height });
    const wide: string[] = [];
    for (const path of routes) {
      await page.goto(path);
      await expect(page.locator("main")).not.toContainText("Loading…");
      if (path.startsWith("/m/") || path.startsWith("/shared/"))
        await expect(page.getByLabel("Bounding box")).toBeVisible();
      if ((await overflow(page)) > 0) wide.push(path);
      const name = `${size.width}${path.replaceAll("/", "-") || "-home"}.png`;
      await info.attach(name, { body: await page.screenshot(), contentType: "image/png" });
    }
    expect(wide).toEqual(size.legacy);
  });
