import { edgePlate } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";
import { cameraPose, distance, holeUnder, near, round, type Vec } from "./viewer";

const views: [string, Vec, Vec][] = [
  ["Top", [0, 0, -1], [0, 1, 0]],
  ["Front", [0, 1, 0], [0, 0, 1]],
  ["Right", [-1, 0, 0], [0, 0, 1]],
];

test("WP-1 viewer loads a GLB, view cube sets camera, orbit", async ({ page, row }) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await page.goto("/m/m1");
  const bbox = page.getByLabel("Bounding box");
  await expect(bbox).toHaveText("120.0 mm × 80.0 mm × 6.0 mm");
  row.measured.glb_bbox = await bbox.textContent();
  await row.shot("1-iso");

  for (const [name, forward, up] of views) {
    await page.getByRole("button", { name }).click();
    await expect.poll(async () => near((await cameraPose(page)).forward, forward, 1e-3)).toBe(true);
    const pose = await cameraPose(page);
    row.measured[`${name.toLowerCase()}_forward`] = round(pose.forward).join(", ");
    row.measured[`${name.toLowerCase()}_up`] = round(pose.up).join(", ");
    expect(near(pose.up, up, 1e-3)).toBe(true);
    await row.shot(`2-${name.toLowerCase()}`);
  }

  await page.getByRole("button", { name: "Top" }).click();
  await expect.poll(async () => near((await cameraPose(page)).forward, [0, 0, -1], 1e-3)).toBe(true);
  const before = await cameraPose(page);
  const box = await page.locator(".viewer canvas").boundingBox();
  if (!box) throw new Error("no canvas");
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  await page.mouse.move(cx + 150, cy + 150);
  await page.mouse.down();
  await page.mouse.move(cx + 30, cy + 60, { steps: 20 });
  await page.mouse.up();
  const after = await cameraPose(page);
  const dot = before.forward.reduce((s, x, i) => s + x * (after.forward[i] ?? 0), 0);
  const angle = (Math.acos(Math.min(1, dot)) * 180) / Math.PI;
  const r0 = distance(before.position, before.target);
  const r1 = distance(after.position, after.target);
  row.measured.orbit_angle_deg = +angle.toFixed(1);
  row.measured.orbit_radius_before_mm = +r0.toFixed(2);
  row.measured.orbit_radius_after_mm = +r1.toFixed(2);
  expect(angle).toBeGreaterThan(10);
  expect(Math.abs(r1 - r0) / r0).toBeLessThan(0.01);
  await row.shot("3-orbited");
  row.note = "Mock API serves the M2 sensor-plate GLB; camera vectors read from the live three.js camera.";
});

test("VM-4 hole-to-edge recommendation shown next to the hole", async ({ page, row }) => {
  const api = new MockApi(edgePlate);
  const finding = api.seed().findings[0];
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toHaveText("60.0 mm × 40.0 mm × 5.0 mm");
  await page.getByRole("button", { name: "Top" }).click();
  await expect.poll(async () => near((await cameraPose(page)).forward, [0, 0, -1], 1e-3)).toBe(true);

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
  Object.assign(row.measured, {
    finding_message: finding?.message ?? null,
    finding_required_mm: finding?.required ?? null,
    hole_enclosed: hole.enclosed,
    hole_diameter_mm: +diameterMm.toFixed(2),
    hole_centre_to_right_edge_mm: +edgeMm.toFixed(2),
    marker_to_hole_centre_mm: +offsetMm.toFixed(2),
  });
  expect(hole.enclosed).toBe(true);
  expect(diameterMm).toBeGreaterThan(8.5);
  expect(diameterMm).toBeLessThan(11);
  expect(Math.abs(edgeMm - 10)).toBeLessThan(1);
  expect(offsetMm).toBeLessThan(2);

  await marker.hover();
  const tip = marker.getByRole("tooltip");
  await expect(tip).toContainText("needs ≥ 15 mm");
  await expect(tip).toContainText("keep hole centres x between -15 and 15");
  row.measured.popup = await tip.textContent();
  await row.shot("popup");
  row.note =
    "Finding, GLB and thumbnail are real geometry-service output for a 60x40x5 plate with a Ø10 hole at x=20; the API leg is mocked.";
});

test("WP-11 report a bug from the editor", async ({ page, row }) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 6.0 mm");
  await page.getByRole("button", { name: "Report a bug" }).click();
  const text = "Top view hides the hole markers";
  await page.getByLabel("What went wrong?").fill(text);
  await row.shot("1-dialog");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("dialog").getByRole("status")).toHaveText("Thanks, the report was saved.");
  await row.shot("2-sent");

  expect(api.bugs).toHaveLength(1);
  const [bug] = api.bugs;
  if (!bug?.screenshot) throw new Error("no screenshot in the report");
  const png = Buffer.from(bug.screenshot.replace(/^data:image\/png;base64,/, ""), "base64");
  const opaque = await page.evaluate(async (src) => {
    const img = new Image();
    img.src = src;
    await img.decode();
    const c = document.createElement("canvas");
    [c.width, c.height] = [img.width, img.height];
    const ctx = c.getContext("2d");
    ctx?.drawImage(img, 0, 0);
    const alpha = ctx?.getImageData(0, 0, c.width, c.height).data.filter((_, i) => i % 4 === 3) ?? [];
    return alpha.filter((a) => a > 128).length / alpha.length;
  }, bug.screenshot);
  Object.assign(row.measured, {
    model_id: bug.model_id,
    version: bug.version,
    text: bug.text,
    screenshot_png: png.subarray(1, 4).toString() === "PNG",
    screenshot_px: `${png.readUInt32BE(16)} x ${png.readUInt32BE(20)}`,
    screenshot_part_coverage: +opaque.toFixed(3),
  });
  expect(bug).toMatchObject({ model_id: "m1", version: 1, text });
  expect(png.subarray(1, 4).toString()).toBe("PNG");
  expect(opaque).toBeGreaterThan(0.01);
  row.note =
    "Web client sends the full report; storage is the mock's POST /bugs (apps/api has no /bugs route yet).";
});
