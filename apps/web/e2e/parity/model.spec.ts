import type { Page } from "@playwright/test";
import type { Component, Version } from "../../src/api";
import { basePlate, motorHolder, stackScenario, type Scenario } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";
import { cameraPose, centre, near, probe, size, type Vec } from "./viewer";

async function openEditor(page: Page, scenario: Scenario) {
  const api = new MockApi(scenario);
  api.seed();
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toBeVisible();
  return api;
}

async function view(page: Page, name: string, forward: Vec) {
  await page.getByRole("button", { name, exact: true }).click();
  await expect.poll(async () => near((await cameraPose(page)).forward, forward, 1e-3)).toBe(true);
}

const getJson = <T>(page: Page, path: string) =>
  page.evaluate((p) => fetch(p).then((r) => r.json()), path) as Promise<T>;

test("AS-1 clicking a component in the viewer selects the id the components API lists", async ({
  page,
  row,
}) => {
  const api = await openEditor(page, stackScenario);
  const listed = await getJson<Component[]>(page, "/models/m1/components?version=1");
  const tree = page.getByRole("list", { name: "Components" });
  await expect(tree.locator("button[data-id]")).toHaveCount(listed.length);
  const nested = tree.locator("li:has(> button[data-id=plate]) ul button[data-id=cube]");
  await expect(nested).toBeVisible();
  await view(page, "Front", [0, 1, 0]);
  await row.shot("1-front");

  const picked: string[] = [];
  for (const c of listed) {
    const { parts } = await probe(page);
    const box = parts[c.name];
    if (!box) throw new Error(`no mesh for ${c.name}`);
    const [[x, y] = [0, 0]] = (await probe(page, [centre(box)])).screen;
    await page.mouse.click(x, y);
    const pressed = tree.locator("button[aria-pressed=true]");
    await expect(pressed).toHaveCount(1);
    const id = (await pressed.getAttribute("data-id")) ?? "";
    picked.push(id);
    await expect(page.getByRole("form", { name: "Refine" }).locator(".chip")).toContainText(c.name);
    row.measured[`click_${c.name}`] = `screen (${x.toFixed(0)}, ${y.toFixed(0)}) -> tree id ${id}`;
    expect(id).toBe(c.id);
    await row.shot(`2-picked-${c.id}`);
  }

  await page.getByLabel("Change request").fill("chamfer the top edges");
  await page.getByRole("button", { name: "Refine" }).click();
  await expect(page.getByRole("list", { name: "Version history" }).locator("strong")).toHaveText([
    "v2",
    "v1",
  ]);
  const refine = api.requests.find((r) => r.path.endsWith("/refine"))?.body as { target?: string };
  Object.assign(row.measured, {
    api_components: listed
      .map((c) => `${c.id} (${c.name}, parent ${c.parent ?? "-"}, joint ${c.joint ?? "-"})`)
      .join("; "),
    picked_ids: picked.join(", "),
    refine_target: refine.target ?? null,
  });
  expect(picked).toEqual(listed.map((c) => c.id));
  expect(refine.target).toBe(listed.at(-1)?.id);
  row.note =
    "GLB is geometry-service output for the D-033 cube-on-plate assembly; the component list is the shape of GET /models/{id}/components (mocked). The viewer maps glTF node names (part names) to API ids.";
});

test("PR-6 select the top face, offset +2 mm: thickness +2, no other parameter changes", async ({
  page,
  row,
}) => {
  const api = await openEditor(page, basePlate);
  await expect(page.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 5.0 mm");
  await view(page, "Top", [0, 0, -1]);
  await page.getByRole("button", { name: "Select face" }).click();
  const [[x, y] = [0, 0]] = (await probe(page, [[10, 10, 5]])).screen;
  await page.mouse.click(x, y);
  const form = page.getByRole("form", { name: "Face edit" });
  await expect(form).toContainText("driven by Thickness (5 mm)");
  await row.shot("1-face-picked");
  const pick = api.requests.find((r) => r.path.endsWith("/face-driver"))?.body as { point: Vec; normal: Vec };

  await form.getByLabel("Offset (mm)").fill("2");
  await form.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByRole("list", { name: "Version history" }).locator("strong")).toHaveText([
    "v2",
    "v1",
  ]);
  await expect(page.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 7.0 mm");
  await expect(page.getByLabel("Thickness", { exact: true })).toHaveValue("7");
  await row.shot("2-offset-applied");

  const patch = api.requests.filter((r) => r.method === "PATCH").map((r) => r.body);
  const [before, after] = api.versions.map((v: Version) =>
    Object.fromEntries(v.params.map((p) => [p.name, p.value])),
  );
  const changed = Object.keys(after ?? {}).filter((k) => after?.[k] !== before?.[k]);
  const height = size(Object.values((await probe(page)).parts)[0] ?? { min: [0, 0, 0], max: [0, 0, 0] })[2];
  Object.assign(row.measured, {
    picked_point: pick.point.map((v) => +v.toFixed(3)).join(", "),
    picked_normal: pick.normal.map((v) => +v.toFixed(3)).join(", "),
    patch: JSON.stringify(patch),
    thickness_before: before?.thickness ?? null,
    thickness_after: after?.thickness ?? null,
    changed_params: changed.join(", "),
    glb_height_mm: +height.toFixed(4),
  });
  expect(pick.normal[2]).toBeGreaterThan(0.999);
  expect(Math.abs(pick.point[2] - 5)).toBeLessThan(0.01);
  expect(patch).toEqual([{ values: { thickness: 7 } }]);
  expect(Math.abs((after?.thickness ?? 0) - (before?.thickness ?? 0) - 2)).toBeLessThanOrEqual(0.01);
  expect(changed).toEqual(["thickness"]);
  expect(Math.abs(height - 7)).toBeLessThanOrEqual(0.01);
  row.note =
    "GLBs for thickness 5 and 7 are geometry-service output. The face-to-parameter lookup is POST /models/{id}/face-driver, mocked here with the plate's top cap; apps/api test_faces.py runs the same flow against the real route and kernel.";
});

test("PR-10 on-model L/W/H labels match the API bounding box", async ({ page, row }) => {
  for (const scenario of [basePlate, motorHolder]) {
    await openEditor(page, scenario);
    const [version] = await getJson<Version[]>(page, "/models/m1/versions");
    const bbox = version?.metrics?.bbox ?? [0, 0, 0];
    const labels = page.locator(".viewer .measure-label");
    await expect(labels).toHaveCount(3);
    const texts = await labels.allTextContents();
    const canvas = await page.locator(".viewer canvas").boundingBox();
    const boxes = await labels.evaluateAll((els) =>
      els.map((e) => e.getBoundingClientRect().toJSON() as DOMRect),
    );
    const inside = boxes.every(
      (b) =>
        canvas &&
        b.x >= canvas.x &&
        b.y >= canvas.y &&
        b.right <= canvas.x + canvas.width &&
        b.bottom <= canvas.y + canvas.height,
    );
    const glb = size(Object.values((await probe(page)).parts)[0] ?? { min: [0, 0, 0], max: [0, 0, 0] });
    const shown = texts.map((t) => Number(/([\d.]+) mm$/.exec(t)?.[1]));
    const key = scenario.title.toLowerCase().replace(/\W+/g, "_");
    Object.assign(row.measured, {
      [`${key}_api_bbox`]: bbox.join(" x "),
      [`${key}_labels`]: texts.join(" | "),
      [`${key}_glb_size`]: glb.map((v) => +v.toFixed(4)).join(" x "),
      [`${key}_labels_inside_view`]: inside,
    });
    expect(texts.map((t) => t.split(" ")[0])).toEqual(["L", "W", "H"]);
    texts.forEach((t) => expect(t).toMatch(/ mm$/));
    shown.forEach((v, i) => expect(Math.abs(v - (bbox[i] ?? NaN))).toBeLessThanOrEqual(0.05));
    glb.forEach((v, i) => expect(Math.abs(v - (bbox[i] ?? NaN))).toBeLessThanOrEqual(0.01));
    expect(inside).toBe(true);
    await row.shot(key);
  }
  row.note =
    "Labels are drawn at the edges of the loaded GLB's box (one decimal); the GLB box is checked against metrics.bbox to 0.01 mm. GLBs and metrics are geometry-service output; the API is mocked.";
});
