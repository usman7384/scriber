import { expect, test } from "../parity/row";
import { basePlate } from "./designs";
import { API, build, project } from "./live";

const apiPath = /^\/(health|projects|models|jobs|batch|shares|s\/|hooks|tokens|bugs|community)/;

test("EX-6 live: share link opens a read-only viewer; revoking it gives 404", async ({
  page,
  browser,
  request,
  row,
}) => {
  const model = await build(request, await project(request, "EX-6 live"), basePlate);
  await page.goto(`/m/${model}`);
  await expect(page.getByLabel("Bounding box")).toBeVisible();
  await page.locator("details.menu summary").click();
  await page.getByRole("button", { name: "Share" }).click();
  const link = await page.getByLabel("Share link").inputValue();
  const share = /\/shared\/([^/]+)$/.exec(link)?.[1] ?? "";
  await row.shot("1-link");

  const visitor = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const visits: string[] = [];
  visitor.on("request", (r) => {
    const path = new URL(r.url()).pathname;
    if (apiPath.test(path)) visits.push(`${r.method()} ${path}`);
  });
  await visitor.goto(link);
  await expect(visitor.getByRole("heading", { level: 1 })).toHaveText("Base plate");
  await expect(visitor.getByText("shared, read-only")).toBeVisible();
  await expect(visitor.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 5.0 mm");
  await expect(visitor.getByRole("table", { name: "Parameters" })).toContainText("Thickness5.00 mm");
  const main = visitor.locator("main");
  const editable = (await main.getByRole("spinbutton").count()) + (await main.getByRole("textbox").count());
  const actions = await main
    .getByRole("button", { name: /Share|Export|Refine|Apply|Restore|Report/ })
    .count();
  await visitor.screenshot({ path: `${row.dir}/2-shared-view.png` });
  const anonymous = await (await request.get(`${API}/s/${share}`)).json();
  const write = await request.patch(`${API}/s/${share}`, { data: {} });

  await page.getByRole("button", { name: "Revoke" }).click();
  await expect(page.locator("details.menu").getByRole("status")).toHaveText("Link revoked");
  await visitor.reload();
  await expect(visitor.getByRole("alert")).toHaveText("share link not found or revoked");
  await visitor.screenshot({ path: `${row.dir}/3-revoked.png` });
  await visitor.close();
  const after = await request.get(`${API}/s/${share}`);

  const seen = [...new Set(visits)];
  Object.assign(row.measured, {
    link,
    shared_requests: seen.join(", "),
    editable_fields: editable,
    edit_buttons: actions,
    api_share_title: (anonymous as { title?: string }).title ?? null,
    write_on_share_status: write.status(),
    api_status_after_revoke: after.status(),
  });
  expect(seen.every((v) => new RegExp(`^GET /s/${share}(/files/\\w+)?$`).test(v))).toBe(true);
  expect(seen).toContain(`GET /s/${share}/files/glb`);
  expect(editable + actions).toBe(0);
  expect(write.status()).toBeGreaterThanOrEqual(400);
  expect(after.status()).toBe(404);
  row.note =
    "Live: POST /shares and DELETE /shares/{id} from the editor; the visitor page is served the real GET /s/{id}.";
});

test("WP-11 live: report a bug from the editor; the API stores model, version, text and the screenshot", async ({
  page,
  request,
  row,
}) => {
  const model = await build(request, await project(request, "WP-11 live"), basePlate);
  await page.goto(`/m/${model}`);
  await expect(page.getByLabel("Bounding box")).toHaveText("120.0 mm × 80.0 mm × 5.0 mm");
  await page.keyboard.press("?");
  await page.getByRole("dialog", { name: "Help" }).getByRole("button", { name: "Report a bug" }).click();
  const text = "Top view hides the hole markers";
  await page.getByLabel("What went wrong?").fill(text);
  await row.shot("1-dialog");
  const sent = page.waitForRequest((r) => r.method() === "POST" && new URL(r.url()).pathname === "/bugs");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("dialog").getByRole("status")).toHaveText("Thanks, the report was saved.");
  await row.shot("2-sent");

  const body = (await sent).postDataJSON() as { screenshot: string };
  const png = Buffer.from(body.screenshot.replace(/^data:image\/png;base64,/, ""), "base64");
  const bugs = (await (await request.get(`${API}/bugs?model_id=${model}`)).json()) as {
    id: string;
    model_id: string;
    version: number;
    text: string;
    user: string;
    screenshot_url: string | null;
  }[];
  const [bug] = bugs;
  const stored = bug?.screenshot_url
    ? await (await request.get(`${API}${bug.screenshot_url}`)).body()
    : Buffer.alloc(0);
  Object.assign(row.measured, {
    stored_bugs: bugs.length,
    model_id: bug?.model_id ?? null,
    version: bug?.version ?? null,
    text: bug?.text ?? null,
    user: bug?.user ?? null,
    screenshot_px: `${png.readUInt32BE(16)} x ${png.readUInt32BE(20)}`,
    screenshot_bytes_sent: png.length,
    screenshot_bytes_stored: stored.length,
    screenshot_identical: stored.equals(png),
  });
  expect(bugs).toHaveLength(1);
  expect(bug).toMatchObject({ model_id: model, version: 1, text, user: "local" });
  expect(png.subarray(1, 4).toString()).toBe("PNG");
  expect(stored.equals(png)).toBe(true);
  row.note =
    "Live: the dialog's POST /bugs is stored by apps/api; the screenshot is read back from /bugs/{id}/screenshot.";
});
