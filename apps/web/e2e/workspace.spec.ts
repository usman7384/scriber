import { expect, test, type Page } from "@playwright/test";
import type { Param } from "../src/api";
import { basePlate, edgePlate, sensorPlate, type Scenario } from "./fixtures";
import { MockApi } from "./mock-api";

async function open(page: Page, scenario: Scenario = sensorPlate) {
  const api = new MockApi(scenario);
  api.seed();
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toHaveText(/ mm$/);
  return api;
}

const inspector = (page: Page) => page.getByRole("complementary", { name: "Inspector" });

test("the canvas is full-bleed and the part sits in the free area between the panels", async ({ page }) => {
  for (const size of [
    { width: 1440, height: 900 },
    { width: 1280, height: 800 },
  ]) {
    await page.setViewportSize(size);
    await open(page);
    const canvas = await page.locator(".viewer canvas").boundingBox();
    expect(canvas).toMatchObject({ x: 0, y: 0, width: size.width, height: size.height });
    const rail = await page.getByRole("complementary", { name: "Structure" }).boundingBox();
    const insp = await inspector(page).boundingBox();
    // the bounding-box chips stand around the part; all of them clear both panels
    const chips = await page
      .locator(".measure-label")
      .evaluateAll((els) => els.map((e) => e.getBoundingClientRect().toJSON() as DOMRect));
    expect(chips).toHaveLength(3);
    for (const c of chips) {
      expect(c.left).toBeGreaterThan((rail?.x ?? 0) + (rail?.width ?? 0));
      expect(c.right).toBeLessThan(insp?.x ?? 0);
    }
  }
});

test("bbox chips are reference dimensions equal to metrics.bbox", async ({ page }) => {
  await open(page);
  await expect(page.locator(".measure-label")).toHaveText(["L 120.0 mm", "W 80.0 mm", "H 6.0 mm"]);
  const paren = await page
    .locator(".measure-label")
    .first()
    .evaluate((e) => getComputedStyle(e, "::before").content + getComputedStyle(e, "::after").content);
  expect(paren).toBe('"("")"');
});

test("picking a face shows the driving chip; typing 7 and Enter sends one PATCH for that parameter", async ({
  page,
}) => {
  const api = await open(page, basePlate);
  await page.getByRole("button", { name: "Top", exact: true }).click();
  await page.getByRole("button", { name: "Select face" }).click();
  await page.waitForTimeout(400);
  const box = await page.locator(".viewer canvas").boundingBox();
  // the free area's centre is the top face of the plate in the top view
  const free = await page.locator(".ws-free").boundingBox();
  if (!box || !free) throw new Error("no canvas");
  await page.mouse.click(free.x + free.width / 2 + 20, free.y + free.height / 2 + 20);
  const chip = page.getByLabel("Thickness, driving dimension");
  await expect(chip).toHaveValue("5.00");
  await expect(inspector(page).getByRole("heading", { name: "Picked face" })).toBeVisible();
  await expect(page.getByRole("list", { name: "Components" })).toContainText("Picked face");
  await chip.click();
  await chip.fill("7");
  await chip.press("Enter");
  await expect(page.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 7.0 mm");
  expect(api.requests.filter((r) => r.method === "PATCH").map((r) => r.body)).toEqual([
    { values: { thickness: 7 } },
  ]);
});

test("the inspector follows the selection and Esc clears it", async ({ page }) => {
  await open(page, edgePlate);
  const heading = inspector(page).locator(".ws-insp-name");
  await expect(heading).toHaveText("Edge test plate");
  await page.getByRole("list", { name: "Components" }).getByRole("button").click();
  await expect(heading).toHaveText("P");
  await page.getByLabel(/^Finding: Ø10 hole/).click();
  await expect(heading).toContainText("Ø10 hole");
  await expect(inspector(page)).toContainText("Measured");
  await page.keyboard.press("Escape");
  await expect(heading).toHaveText("Edge test plate");
});

test("finding pins are reachable by Tab and open their callout", async ({ page }) => {
  await open(page, edgePlate);
  const pin = page.getByLabel(/^Finding: Ø10 hole/);
  await expect(pin).toHaveAccessibleName(/, error$/);
  await page.getByRole("button", { name: "Dimensions" }).focus();
  for (let i = 0; i < 6 && !(await pin.evaluate((e) => e === document.activeElement)); i++)
    await page.keyboard.press("Tab");
  await expect(pin).toBeFocused();
  await expect(pin.getByRole("tooltip")).toBeVisible();
  await expect(pin.getByRole("button", { name: "Ask agent to fix" })).toBeVisible();
});

test("every parameter shows its monogram, quote and ref on demand; defaults count as assumptions", async ({
  page,
}) => {
  const api = new MockApi();
  api.seed();
  const assumed: Param = {
    name: "edge_offset",
    label: "Edge offset",
    value: 10,
    unit: "mm",
    description: "hole centre to edge",
    provenance: { source: "default" },
  };
  api.versions.forEach((v) => (v.params = [...v.params, assumed]));
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toBeVisible();
  const source = page.getByRole("button", { name: "Source of Plate Length: document" });
  await expect(source).toHaveText("DOC");
  await source.click();
  const pop = page.getByRole("dialog", { name: "Where this value comes from" });
  await expect(pop).toContainText("REQ-1 Plate size 120 x 80 x 6 mm");
  await expect(pop).toContainText("spec.pdf#p1:l2");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: /^Checks: .* 1 assumed$/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Source of Edge offset: default" })).toHaveText("DEF");
});

test("HUD keys switch views and toggles", async ({ page }) => {
  await open(page);
  await page.locator("body").click({ position: { x: 5, y: 890 } });
  await page.keyboard.press("1");
  await expect(page.getByRole("button", { name: "Top" })).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("0");
  await expect(page.getByRole("button", { name: "Iso" })).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("e");
  await expect(page.getByRole("button", { name: "Edges" })).toHaveAttribute("aria-pressed", "false");
  await page.keyboard.press("m");
  await expect(page.locator(".measure-label")).toHaveCount(0);
  await page.keyboard.press("p");
  await expect(page.getByRole("button", { name: "Select face" })).toHaveAttribute("aria-pressed", "true");
});

test("mobile: a bottom sheet with three snap points, no horizontal scroll", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page);
  // the shell's own top bar (package A2) still sits under the workspace; the workspace itself must fit
  const scroll = await page.locator(".ws").evaluate((e) => e.scrollWidth);
  expect(scroll).toBeLessThanOrEqual(390);
  const dock = page.locator(".ws-dock");
  const heights: number[] = [];
  for (let i = 0; i < 3; i++) {
    heights.push(Math.round((await dock.boundingBox())?.height ?? 0));
    await page.getByRole("button", { name: "Resize panel" }).click();
    await page.waitForTimeout(300);
  }
  expect(heights[0]).toBeLessThan(heights[1] ?? 0);
  expect(heights[1]).toBeLessThan(heights[2] ?? 0);
  await page.getByRole("tab", { name: "Versions" }).click();
  await expect(page.getByRole("list", { name: "Version history" })).toBeVisible();
  await expect(inspector(page)).toBeHidden();
});

// SHOTS=dir npx playwright test workspace -g screenshots
test("screenshots", async ({ page }) => {
  test.skip(!process.env.SHOTS, "set SHOTS to an output folder");
  test.setTimeout(120_000);
  for (const theme of ["dark", "light"])
    for (const [name, size] of [
      ["1440", { width: 1440, height: 900 }],
      ["390", { width: 390, height: 844 }],
    ] as const) {
      await page.setViewportSize(size);
      await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
      await open(page);
      const free = await page.locator(".ws-free").boundingBox();
      if (!free) throw new Error("no free frame");
      await page.mouse.click(free.x + free.width * 0.4, free.y + free.height * 0.45);
      if (name === "1440")
        await page
          .getByLabel(/^Finding: /)
          .first()
          .hover();
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${process.env.SHOTS}/workspace-${theme}-${name}.png` });
    }
});
