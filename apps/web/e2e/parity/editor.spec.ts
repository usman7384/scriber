import type { Page } from "@playwright/test";
import { edgePlate, sensorPlate } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";

const patches = (api: MockApi) => api.requests.filter((r) => r.method === "PATCH");

async function openEditor(page: Page, api: MockApi) {
  api.seed();
  await page.unrouteAll();
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toBeVisible();
}

async function drag(page: Page, label: string, fromFraction: number, toFraction: number) {
  const box = await page.getByLabel(`${label} slider`).boundingBox();
  if (!box) throw new Error("no slider");
  const y = box.y + box.height / 2;
  await page.mouse.move(box.x + box.width * fromFraction, y);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * toFraction, y, { steps: 12 });
  await page.mouse.up();
  return Date.now();
}

test("PR-1 parameter panel: one row per param with slider, numeric field and unit", async ({ page, row }) => {
  for (const scenario of [sensorPlate, edgePlate]) {
    await openEditor(page, new MockApi(scenario));
    const rows = page.getByRole("form", { name: "Parameters" }).locator(".param");
    await expect(rows).toHaveCount(scenario.params.length);
    for (const [i, p] of scenario.params.entries()) {
      const r = rows.nth(i);
      await expect(r.locator("label")).toHaveText(p.label);
      const slider = r.getByRole("slider", { name: `${p.label} slider` });
      await expect(slider).toBeVisible();
      if (p.min != null) await expect(slider).toHaveAttribute("min", String(p.min));
      if (p.max != null) await expect(slider).toHaveAttribute("max", String(p.max));
      await expect(r.getByRole("spinbutton", { name: p.label })).toHaveValue(String(p.value));
      await expect(r.locator(".unit")).toHaveText(p.unit);
      row.measured[`${scenario.title}: ${p.label}`] =
        `slider ${await slider.getAttribute("min")}..${await slider.getAttribute("max")}, field ${p.value}, unit ${p.unit}`;
    }
    await row.shot(scenario.title.toLowerCase().replace(/\W+/g, "-"));
  }
  row.note = "Web half only: params come from the mock API in the documented shape.";
});

test("PR-3 apply instantly off waits for Enter, on regenerates once after a debounce", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  await openEditor(page, api);
  const history = page.getByRole("list", { name: "Version history" });
  const field = page.getByLabel("Plate Length", { exact: true });

  await drag(page, "Plate Length", 0.5, 0.7);
  const dragged = await field.inputValue();
  await page.waitForTimeout(1000);
  row.measured.off_value_after_drag = Number(dragged);
  row.measured.off_patches_1s_after_drag = patches(api).length;
  expect(Number(dragged)).not.toBe(120);
  expect(patches(api)).toHaveLength(0);
  await row.shot("1-off-dragged");

  await page.getByLabel("Plate Length slider").press("Enter");
  await expect(history.locator("strong")).toHaveText(["v2", "v1"]);
  row.measured.off_patches_after_enter = patches(api).length;
  expect(patches(api).map((r) => r.body)).toEqual([{ values: { plate_length: Number(dragged) } }]);
  await row.shot("2-off-applied");

  await page.getByLabel("Apply instantly").check();
  const released = await drag(page, "Plate Length", 0.6, 0.4);
  const value = Number(await field.inputValue());
  await expect(history.locator("strong")).toHaveText(["v3", "v2", "v1"]);
  await page.waitForTimeout(800);
  const instant = patches(api).slice(1);
  row.measured.on_patches_after_drag = instant.length;
  row.measured.on_debounce_ms = (instant[0]?.at ?? 0) - released;
  expect(instant.map((r) => r.body)).toEqual([{ values: { plate_length: value } }]);
  expect(instant[0]?.at ?? 0).toBeGreaterThanOrEqual(released + 300);
  await expect(field).toHaveValue(String(value));
  await row.shot("3-on-applied");
  row.note = "PATCH /models/m1/params is mocked; the new version comes back over the mocked job stream.";
});

test("WP-3 editor header and target chip", async ({ page, row }) => {
  const api = new MockApi();
  await openEditor(page, api);
  const title = api.models[0]?.title ?? "";
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  await expect(page.getByRole("link", { name: "← Project" })).toBeVisible();
  await expect(page.getByRole("link", { name: "New generation" })).toBeVisible();
  const chip = page.getByRole("form", { name: "Refine" }).locator(".chip");
  const states: string[] = [];
  const note = async () => states.push((await chip.textContent())?.replace("Clear", "").trim() ?? "");

  await expect(chip).toHaveText("Target: Entire object");
  await note();
  await page.getByRole("list", { name: "Components" }).getByRole("button").click();
  await expect(chip).toContainText("Target: Sensor mounting plate");
  await note();
  await row.shot("1-component-target");
  await chip.getByRole("button", { name: "Clear" }).click();
  await expect(chip).toHaveText("Target: Entire object");
  await note();

  await page.getByRole("button", { name: "Top" }).click();
  const canvas = page.locator(".viewer canvas");
  await canvas.click({ position: { x: 300, y: 260 } });
  await expect(chip).toContainText("Target: Sensor mounting plate");
  await note();
  await row.shot("2-picked-in-viewer");
  await canvas.click({ position: { x: 20, y: 20 } });
  await expect(chip).toHaveText("Target: Entire object");
  await note();

  row.measured.title = title;
  row.measured.chip_states = states.join(" | ");
  await page.getByRole("link", { name: "New generation" }).click();
  await expect(page).toHaveURL(/\/p\/p1$/);
  await expect(page.getByLabel("Describe the part")).toBeVisible();
  await page.goBack();
  await page.getByRole("link", { name: "← Project" }).click();
  await expect(page).toHaveURL(/\/p\/p1$/);
  row.measured.back_and_new_generation = "both reach the project prompt";
  row.note = "Title is the API model title (GE-10 makes it on the server; mocked here).";
});

test("WP-8 thumbnails for models and versions, new one after an edit", async ({ page, row }) => {
  const api = new MockApi(edgePlate);
  api.seed();
  await api.install(page);
  const size = (img: ReturnType<Page["locator"]>) =>
    img.evaluate((i: HTMLImageElement) => `${i.naturalWidth}x${i.naturalHeight}`);

  await page.goto("/p/p1");
  const card = page.getByRole("list", { name: "Models" }).locator("img");
  await expect.poll(() => size(card)).toBe("256x256");
  row.measured.model_card = await size(card);

  await page.goto("/m/m1");
  const thumbs = page.getByRole("list", { name: "Version history" }).locator("img");
  await expect.poll(() => size(thumbs.first())).toBe("256x256");
  const field = page.getByLabel("Hole X", { exact: true });
  await field.fill("15");
  await field.press("Enter");
  await expect(thumbs).toHaveCount(2);
  await expect.poll(() => size(thumbs.first())).toBe("256x256");
  const srcs = await thumbs.evaluateAll((imgs: HTMLImageElement[]) => imgs.map((i) => i.src));
  const changed = await thumbs.evaluateAll((imgs: HTMLImageElement[]) => {
    const pixels = (img: HTMLImageElement) => {
      const c = document.createElement("canvas");
      [c.width, c.height] = [img.naturalWidth, img.naturalHeight];
      const ctx = c.getContext("2d");
      ctx?.drawImage(img, 0, 0);
      return ctx?.getImageData(0, 0, c.width, c.height).data ?? new Uint8ClampedArray();
    };
    const [a, b] = imgs.map(pixels);
    return a && b ? a.filter((v, i) => Math.abs(v - (b[i] ?? 0)) > 16).length / a.length : 0;
  });
  const types = await page.evaluate(
    (urls) => Promise.all(urls.map((u) => fetch(u).then((r) => r.headers.get("content-type")))),
    srcs,
  );
  Object.assign(row.measured, {
    version_thumbs: srcs.length,
    version_thumb_size: await size(thumbs.first()),
    distinct_urls: new Set(srcs).size === srcs.length,
    content_types: types.join(", "),
    changed_pixel_fraction: +changed.toFixed(3),
  });
  expect(new Set(srcs).size).toBe(2);
  expect(types).toEqual(["image/png", "image/png"]);
  expect(changed).toBeGreaterThan(0.001);
  await row.shot("1-history");
  await page.goto("/p/p1");
  await expect.poll(() => card.evaluate((i: HTMLImageElement) => i.src)).toBe(srcs[0]);
  await row.shot("2-gallery");
  row.note =
    "PNGs are real 256 px renders from the geometry service for hole x=20 and x=15; the mock API stands in for regeneration on edit.";
});
