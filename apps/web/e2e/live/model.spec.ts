import type { APIRequestContext, Page } from "@playwright/test";
import type { Component, Version } from "../../src/api";
import { expect, test } from "../parity/row";
import { cameraPose, centre, holeUnder, near, probe, size, type Vec } from "../parity/viewer";
import { basePlate, edgePlate, stack } from "./designs";
import { build, getJson, project, versions } from "./live";

async function openModel(
  page: Page,
  request: APIRequestContext,
  name: string,
  design: object,
  status: "done" | "failed" = "done",
) {
  const model = await build(request, await project(request, name), design, status);
  await page.goto(`/m/${model}`);
  await expect(page.getByLabel("Bounding box")).toBeVisible();
  return model;
}

async function view(page: Page, name: string, forward: Vec) {
  await page.getByRole("button", { name, exact: true }).click();
  await expect.poll(async () => near((await cameraPose(page)).forward, forward, 1e-3)).toBe(true);
}

const values = (v?: Version) => Object.fromEntries((v?.params ?? []).map((p) => [p.name, p.value]));

test("PR-6 live: select the top face, offset +2 mm: thickness +2, no other parameter changes", async ({
  page,
  request,
  row,
}) => {
  const model = await openModel(page, request, "PR-6 live", basePlate);
  await expect(page.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 5.0 mm");
  await view(page, "Top", [0, 0, -1]);
  await page.getByRole("button", { name: "Select face" }).click();
  const picked = page.waitForRequest((r) => r.url().endsWith("/face-driver"));
  const [[x, y] = [0, 0]] = (await probe(page, [[10, 10, 5]])).screen;
  await page.mouse.click(x, y);
  const pick = (await picked).postDataJSON() as { point: Vec; normal: Vec };
  const form = page.getByRole("form", { name: "Face edit" });
  await expect(form).toContainText("driven by Thickness (5 mm)");
  await row.shot("1-face-picked");

  const patched = page.waitForRequest((r) => r.method() === "PATCH");
  await form.getByLabel("Offset (mm)").fill("2");
  await form.getByRole("button", { name: "Apply" }).click();
  const patch = (await patched).postDataJSON() as object;
  await expect(page.getByRole("list", { name: "Version history" }).locator("strong")).toHaveText([
    "v2",
    "v1",
  ]);
  await expect(page.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 7.0 mm");
  await expect(page.getByLabel("Thickness", { exact: true })).toHaveValue("7");
  await row.shot("2-offset-applied");

  const [v1, v2] = (await versions(request, model)).sort((a, b) => a.number - b.number);
  const [before, after] = [values(v1), values(v2)];
  const changed = Object.keys(after).filter((k) => after[k] !== before[k]);
  const height = size(Object.values((await probe(page)).parts)[0] ?? { min: [0, 0, 0], max: [0, 0, 0] })[2];
  Object.assign(row.measured, {
    picked_point: pick.point.map((v) => +v.toFixed(3)).join(", "),
    picked_normal: pick.normal.map((v) => +v.toFixed(3)).join(", "),
    patch: JSON.stringify(patch),
    v2_origin: v2?.origin ?? null,
    thickness_before: before.thickness ?? null,
    thickness_after: after.thickness ?? null,
    changed_params: changed.join(", "),
    api_bbox_after: v2?.metrics?.bbox.join(" x ") ?? null,
    glb_height_mm: +height.toFixed(4),
  });
  expect(pick.normal[2]).toBeGreaterThan(0.999);
  expect(Math.abs(pick.point[2] - 5)).toBeLessThan(0.01);
  expect(patch).toEqual({ values: { thickness: 7 } });
  expect(Math.abs((after.thickness ?? 0) - (before.thickness ?? 0) - 2)).toBeLessThanOrEqual(0.01);
  expect(changed).toEqual(["thickness"]);
  expect(Math.abs((v2?.metrics?.bbox[2] ?? 0) - 7)).toBeLessThanOrEqual(0.01);
  expect(Math.abs(height - 7)).toBeLessThanOrEqual(0.01);
  row.note = "Live: real face-driver route, PATCH rebuild on the kernel and the GLB it exported.";
});

test("PR-10 live: on-model L/W/H labels match the API bounding box", async ({ page, request, row }) => {
  for (const [key, design] of [
    ["base_plate", basePlate],
    ["stack", stack],
  ] as const) {
    const model = await openModel(page, request, `PR-10 live ${key}`, design);
    const bbox = (await versions(request, model))[0]?.metrics?.bbox ?? [0, 0, 0];
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
    const parts = Object.values((await probe(page)).parts);
    const lo = [0, 1, 2].map((i) => Math.min(...parts.map((p) => p.min[i] ?? 0)));
    const hi = [0, 1, 2].map((i) => Math.max(...parts.map((p) => p.max[i] ?? 0)));
    const glb = hi.map((h, i) => h - (lo[i] ?? 0));
    const shown = texts.map((t) => Number(/([\d.]+) mm$/.exec(t)?.[1]));
    Object.assign(row.measured, {
      [`${key}_api_bbox`]: bbox.join(" x "),
      [`${key}_labels`]: texts.join(" | "),
      [`${key}_glb_size`]: glb.map((v) => +v.toFixed(4)).join(" x "),
      [`${key}_labels_inside_view`]: inside,
    });
    expect(texts.map((t) => t.split(" ")[0])).toEqual(["L", "W", "H"]);
    shown.forEach((v, i) => expect(Math.abs(v - (bbox[i] ?? NaN))).toBeLessThanOrEqual(0.05));
    glb.forEach((v, i) => expect(Math.abs(v - (bbox[i] ?? NaN))).toBeLessThanOrEqual(0.01));
    expect(inside).toBe(true);
    await row.shot(key);
  }
  row.note =
    "Live: designs built by apps/api; metrics.bbox from the API, labels and GLB box from the viewer.";
});

test("VM-4 live: hole-to-edge recommendation from the API shown next to the hole", async ({
  page,
  request,
  row,
}) => {
  // The error-severity finding fails the version; the API still keeps its files, findings and thumbnail.
  const model = await openModel(page, request, "VM-4 live", edgePlate(20), "failed");
  const finding = (await versions(request, model))[0]?.findings.find((f) => f.rule_id.includes("hole_edge"));
  await expect(page.getByLabel("Bounding box")).toHaveText("60.0 mm × 40.0 mm × 5.0 mm");
  await view(page, "Top", [0, 0, -1]);

  const marker = page.getByLabel(/^Finding: Ø10 hole/);
  await expect(marker).toBeVisible();
  const mb = await marker.boundingBox();
  if (!mb) throw new Error("no marker box");
  const at = { x: mb.x + mb.width / 2, y: mb.y + mb.height / 2 };
  const hole = await holeUnder(page, at);
  expect(hole, "marker is not over a see-through region").not.toBeNull();
  if (!hole) return;
  const mmPerPx = 60 / (hole.plateRightPx - hole.plateLeftPx);
  const offsetMm = Math.hypot(at.x - hole.centre[0], at.y - hole.centre[1]) * mmPerPx;
  const diameterMm = hole.diameterPx * mmPerPx;
  const edgeMm = (hole.plateRightPx - hole.centre[0]) * mmPerPx;
  await marker.hover();
  const tip = marker.getByRole("tooltip");
  await expect(tip).toContainText(finding?.message ?? "no hole-edge finding from the API");
  Object.assign(row.measured, {
    api_finding: finding ? `${finding.rule_id}: ${finding.message}` : null,
    api_suggestion: finding?.suggestion ?? null,
    api_required_mm: finding?.required ?? null,
    hole_enclosed: hole.enclosed,
    hole_diameter_mm: +diameterMm.toFixed(2),
    hole_centre_to_right_edge_mm: +edgeMm.toFixed(2),
    marker_to_hole_centre_mm: +offsetMm.toFixed(2),
    popup: (await tip.textContent()) ?? "",
  });
  await row.shot("popup");
  expect(finding?.required).toBe(15);
  expect(hole.enclosed).toBe(true);
  expect(diameterMm).toBeGreaterThan(8.5);
  expect(diameterMm).toBeLessThan(11);
  expect(Math.abs(edgeMm - 10)).toBeLessThan(1);
  expect(offsetMm).toBeLessThan(2);
  await expect(tip).toContainText("needs ≥ 15 mm");
  await expect(tip).toContainText(finding?.suggestion ?? "no suggestion");
  row.note =
    "Live: the finding is apps/api's DFM output with the project's default hole-edge rule (1.5 x D).";
});

test("AS-1 live: clicking a component in the viewer selects the id the components API lists", async ({
  page,
  request,
  row,
}) => {
  const model = await openModel(page, request, "AS-1 live", stack);
  const listed = await getJson<Component[]>(request, `/models/${model}/components?version=1`);
  const tree = page.getByRole("list", { name: "Components" });
  await expect(tree.locator("button[data-id]")).toHaveCount(listed.length);
  await view(page, "Front", [0, 1, 0]);
  await row.shot("1-front");

  const picked: string[] = [];
  for (const c of listed) {
    const box = (await probe(page)).parts[c.name];
    if (!box) throw new Error(`no mesh for ${c.name}`);
    const [[x, y] = [0, 0]] = (await probe(page, [centre(box)])).screen;
    await page.mouse.click(x, y);
    const pressed = tree.locator("button[aria-pressed=true]");
    await expect(pressed).toHaveCount(1);
    const id = (await pressed.getAttribute("data-id")) ?? "";
    picked.push(id);
    await expect(page.getByRole("form", { name: "Refine" }).locator(".chip")).toContainText(c.name);
    row.measured[`click_${c.name}`] = `screen (${x.toFixed(0)}, ${y.toFixed(0)}) -> tree id ${id}`;
    await row.shot(`2-picked-${c.id}`);
  }
  const nested = await tree.locator("li:has(> button[data-id=plate]) ul button[data-id=cube]").count();
  Object.assign(row.measured, {
    api_components: listed
      .map((c) => `${c.id} (${c.name}, parent ${c.parent ?? "-"}, joint ${c.joint ?? "-"})`)
      .join("; "),
    picked_ids: picked.join(", "),
    cube_nested_under_plate: nested === 1,
  });
  expect(picked).toEqual(listed.map((c) => c.id));
  expect(nested).toBe(1);
  row.note =
    "Live: the D-033 cube-on-plate assembly built by apps/api; components from GET /models/{id}/components. Refine with the selection as target is not run here (it needs a model call).";
});

test("WP-8 live: 256 px thumbnails for models and versions, regenerated server-side on edit", async ({
  page,
  request,
  row,
}) => {
  const id = await project(request, "WP-8 live");
  const model = await build(request, id, edgePlate(15));
  const natural = (img: ReturnType<Page["locator"]>) =>
    img.evaluate((i: HTMLImageElement) => `${i.naturalWidth}x${i.naturalHeight}`);

  await page.goto(`/p/${id}`);
  const card = page.getByRole("list", { name: "Models" }).locator("img");
  await expect.poll(() => natural(card)).toBe("256x256");
  row.measured.model_card = await natural(card);

  await page.goto(`/m/${model}`);
  const thumbs = page.getByRole("list", { name: "Version history" }).locator("img");
  await expect.poll(() => natural(thumbs.first())).toBe("256x256");
  const field = page.getByLabel("Hole X", { exact: true });
  await field.fill("10");
  await field.press("Enter");
  await expect(thumbs).toHaveCount(2);
  await expect.poll(() => natural(thumbs.first())).toBe("256x256");
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
  const listed = await versions(request, model);
  Object.assign(row.measured, {
    versions: listed
      .map((v) => `v${v.number} ${v.origin} hole_x ${values(v).hole_x} ${v.thumbnail_url}`)
      .join("; "),
    version_thumb_size: await natural(thumbs.first()),
    distinct_urls: new Set(srcs).size === srcs.length,
    content_types: types.join(", "),
    changed_pixel_fraction: +changed.toFixed(3),
  });
  expect(listed.map((v) => values(v).hole_x)).toEqual([15, 10]);
  expect(new Set(srcs).size).toBe(2);
  expect(types).toEqual(["image/png", "image/png"]);
  expect(changed).toBeGreaterThan(0.001);
  await row.shot("1-history");
  await page.goto(`/p/${id}`);
  await expect.poll(() => card.evaluate((i: HTMLImageElement) => i.src)).toBe(srcs[0]);
  await row.shot("2-gallery");
  row.note =
    "Live: thumbnails rendered by apps/api for each version (pyrender), including the PATCH rebuild.";
});
