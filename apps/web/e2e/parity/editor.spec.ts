import type { Page } from "@playwright/test";
import { edgePlate, sensorPlate } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";
import { probe, type Vec } from "./viewer";

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
  const project = page
    .getByRole("navigation", { name: "Location" })
    .getByRole("link", { name: "Bracket lab" });
  await expect(project).toBeVisible();
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
  // a point on the plate's top face between its holes, and one on the ground beside it
  const plate = Object.values((await probe(page)).parts)[0];
  if (!plate) throw new Error("no plate");
  const [min, max] = [plate.min, plate.max];
  const points: Vec[] = [
    [min[0] + (max[0] - min[0]) * 0.75, (min[1] + max[1]) / 2, max[2]],
    [min[0] - 10, min[1] - 10, min[2]],
  ];
  const [onPart = [0, 0], offPart = [0, 0]] = (await probe(page, points)).screen;
  await page.mouse.click(...onPart);
  await expect(chip).toContainText("Target: Sensor mounting plate");
  await note();
  await row.shot("2-picked-in-viewer");
  await page.mouse.click(...offPart);
  await expect(chip).toHaveText("Target: Entire object");
  await note();

  row.measured.title = title;
  row.measured.chip_states = states.join(" | ");
  await project.click();
  await expect(page).toHaveURL(/\/p\/p1$/);
  await expect(page.getByLabel("Describe the part")).toBeVisible();
  row.measured.back_and_new_generation = "the breadcrumb's project link reaches the project prompt";
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

test("PR-7 suggestions with accept and ignore in the editor", async ({ page, row }) => {
  const api = new MockApi(edgePlate);
  await openEditor(page, api);
  const panel = page.getByRole("region", { name: "Suggestions" });
  const history = page.getByRole("list", { name: "Version history" });
  const items = panel.locator("li");
  await expect(panel).toContainText("No open suggestions.");
  await panel.getByRole("button", { name: "Suggest changes" }).click();
  await expect(items).toHaveCount(2);
  await expect(items.first()).toContainText("Hole X 20 → 15 mm");
  await expect(items.first()).toContainText("1.5 x its diameter");
  await row.shot("1-suggestions");

  await items.nth(1).getByRole("button", { name: "Ignore" }).click();
  await expect(items).toHaveCount(1);
  await page.waitForTimeout(500);
  const afterIgnore = { versions: api.versions.length, patches: patches(api).length };
  await expect(history.locator("strong")).toHaveText(["v1"]);
  await row.shot("2-ignored");

  await expect(page.getByLabel(/^Finding: /)).toHaveCount(1);
  await items.first().getByRole("button", { name: "Accept" }).click();
  await expect(history.locator("strong")).toHaveText(["v2", "v1"]);
  await expect(history.locator("li").first()).toContainText("suggestion");
  await expect(page.getByLabel("Hole X", { exact: true })).toHaveValue("15");
  await expect(page.getByLabel(/^Finding: /)).toHaveCount(0);
  await expect(panel).toContainText("No open suggestions.");
  await row.shot("3-accepted");

  const calls = api.requests
    .filter((r) => r.path.includes("/suggestions"))
    .map((r) => `${r.method} ${r.path}`);
  const [v1, v2] = api.versions;
  Object.assign(row.measured, {
    suggestion_calls: calls.join(", "),
    versions_after_ignore: afterIgnore.versions,
    param_patches_after_ignore: afterIgnore.patches,
    accepted_origin: v2?.origin ?? null,
    hole_x: `${v1?.params[0]?.value} -> ${v2?.params[0]?.value}`,
    findings: `${v1?.findings.length} -> ${v2?.findings.length}`,
    statuses: api.suggestions.map((s) => `${s.id} ${s.status}`).join(", "),
  });
  expect(afterIgnore).toEqual({ versions: 1, patches: 0 });
  expect(v2).toMatchObject({ origin: "suggestion" });
  expect(v2?.params[0]?.value).toBe(15);
  expect(api.suggestions.map((s) => s.status)).toEqual(["accepted", "ignored"]);
  row.note =
    "Suggestion routes are mocked in the apps/api shapes (ignore returns the suggestion); accepting rebuilds through the mocked job stream with real geometry for hole x = 15. Bubbles anchored in the 3D view are not built; suggestions are a panel.";
});
