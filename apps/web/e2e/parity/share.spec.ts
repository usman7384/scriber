import { MockApi } from "../mock-api";
import { expect, test } from "./row";

test("EX-6 share link opens a read-only viewer; revoking it gives 404", async ({ page, browser, row }) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toBeVisible();
  await page.getByRole("button", { name: "Share" }).click();
  const link = await page.getByLabel("Share link").inputValue();
  await row.shot("1-link");

  const visitor = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await api.install(visitor);
  const before = api.requests.length;
  await visitor.goto(link);
  await expect(visitor.getByRole("heading", { level: 1 })).toHaveText("Sensor plate");
  await expect(visitor.getByText("shared, read-only")).toBeVisible();
  await expect(visitor.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 6.0 mm");
  await expect(visitor.getByRole("table", { name: "Parameters" })).toContainText("Plate Length120 mm");
  const editable = await visitor.locator("main").getByRole("spinbutton").count();
  const textboxes = await visitor.locator("main").getByRole("textbox").count();
  const actions = await visitor
    .locator("main")
    .getByRole("button", { name: /Share|Export|Refine|Apply|Restore|Report/ })
    .count();
  await visitor.screenshot({ path: `${row.dir}/2-shared-view.png` });
  const visits = api.requests.slice(before).map((r) => `${r.method} ${r.path}`);

  await page.getByRole("button", { name: "Revoke" }).click();
  await expect(page.getByRole("status")).toHaveText("Link revoked");
  await visitor.reload();
  await expect(visitor.getByRole("alert")).toHaveText("share link not found or revoked");
  await visitor.screenshot({ path: `${row.dir}/3-revoked.png` });
  await visitor.close();

  Object.assign(row.measured, {
    link,
    shared_requests: [...new Set(visits)].join(", "),
    editable_fields: editable + textboxes,
    edit_buttons: actions,
    after_revoke: "share link not found or revoked",
  });
  expect(link).toMatch(/\/shared\/s1$/);
  expect(visits.every((v) => /^GET \/s\/s1(\/files\/\w+)?$/.test(v))).toBe(true);
  expect(visits).toContain("GET /s/s1/files/glb");
  expect(editable + textboxes + actions).toBe(0);
  row.note =
    "Viewer page /shared/{id} reads only GET /s/{id} and its files (mocked in the apps/api shape); the API half (no auth, write 401, revoked 404) is parity-20261029-025007.";
});
