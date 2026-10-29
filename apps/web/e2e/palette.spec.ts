import { expect, test, type Page } from "@playwright/test";
import { MockApi } from "./mock-api";

const palette = (page: Page) => page.getByRole("combobox", { name: "Search actions, parameters and places" });

async function run(page: Page, query: string, option: string | RegExp = query) {
  await page.keyboard.press("Control+k");
  await palette(page).fill(query);
  await page
    .getByRole("listbox", { name: "Command palette" })
    .getByRole("option", { name: option })
    .first()
    .click();
  await expect(palette(page)).toBeHidden();
}

test.beforeEach(async ({ page }) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
});

test("Ctrl+K opens the palette on every route and Esc returns focus", async ({ page }) => {
  for (const path of [
    "/",
    "/library",
    "/explore",
    "/settings",
    "/p/p1",
    "/p/p1/context",
    "/m/m1",
    "/shared/s1",
  ]) {
    await page.goto(path);
    await expect(page.locator("main")).not.toContainText("Loading…");
    await page.keyboard.press("Control+k");
    await expect(palette(page), path).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(palette(page), path).toBeHidden();
  }
  await page.goto("/");
  const library = page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Library" });
  await library.focus();
  await page.keyboard.press("Control+k");
  await expect(palette(page)).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(library).toBeFocused();
});

test("the palette reaches every route", async ({ page }) => {
  await page.goto("/");
  const steps: [string, string | RegExp, RegExp][] = [
    ["library", "Library", /\/library$/],
    ["community", "Community", /\/explore$/],
    ["bracket", /^Bracket lab/, /\/p\/p1$/],
    ["sources bracket", /Sources · Bracket lab/, /\/p\/p1\/context$/],
    ["sensor plate", /^Sensor plate/, /\/m\/m1$/],
    ["projects", "Projects", /\/$/],
    ["settings", /^Settings$/, /\/settings$/],
  ];
  for (const [query, option, url] of steps) {
    await run(page, query, option);
    await expect(page).toHaveURL(url);
  }
  await expect(page.getByRole("dialog", { name: "Settings" })).toBeVisible();
  await run(page, "help", /^Help/);
  await expect(page).toHaveURL(/\/help$/);
  await expect(page.getByRole("dialog", { name: "Help" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/\/$/);
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog", { name: "Help" })).toBeVisible();
});

test("the palette sets theme and language, and system follows the OS", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  const html = page.locator("html");
  await expect(html).toHaveAttribute("data-theme", "dark");
  await run(page, "theme light", /Light/);
  await expect(html).toHaveAttribute("data-theme", "light");
  await run(page, "theme system", /System/);
  await expect(html).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(html).toHaveAttribute("data-theme", "light");

  await run(page, "deutsch", /Deutsch/);
  await expect(html).toHaveAttribute("lang", "de");
  await expect(page.getByRole("navigation", { name: "Hauptmenü" })).toContainText("Projekte");
});

test("registered actions run from the palette", async ({ page }) => {
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toBeVisible();
  await run(page, "report", /Report a bug/);
  await expect(page.getByRole("dialog", { name: "Report a bug" })).toBeVisible();
  await page.keyboard.press("Escape");
  await run(page, "help", /^Help/);
  await page.getByRole("dialog", { name: "Help" }).getByRole("button", { name: "Report a bug" }).click();
  await expect(page.getByRole("dialog", { name: "Report a bug" })).toBeVisible();
});
