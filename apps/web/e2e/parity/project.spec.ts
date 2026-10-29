import { asset, shopModels } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";

test("WP-2 prompt card with image, mesh and spec attachments makes one generation job", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  await api.install(page);
  await page.goto("/p/p1");
  const attachments = [
    { kind: "+ Image", name: "plate-photo.png", mimeType: "image/png", buffer: asset("plate.png") },
    { kind: "+ Mesh", name: "old-plate.glb", mimeType: "model/gltf-binary", buffer: asset("plate.glb") },
    {
      kind: "+ Spec file",
      name: "plate-spec.md",
      mimeType: "text/markdown",
      buffer: Buffer.from("# Plate\nREQ-1 Plate size 120 x 80 x 6 mm\n"),
    },
  ];
  for (const { kind, ...file } of attachments) await page.getByLabel(kind).setInputFiles(file);
  await expect(page.getByRole("list", { name: "Attachments" }).getByRole("listitem")).toHaveCount(3);
  await page.getByLabel("Describe the part").fill("Copy this plate but 120 x 80 x 6 mm");
  await row.shot("1-attached");
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByRole("region", { name: "Generation timeline" }).getByRole("status")).toHaveText(
    "done",
  );
  await row.shot("2-generated");

  const uploaded = api.files.filter((f) => attachments.some((a) => a.name === f.name)).map((f) => f.id);
  const generates = api.requests.filter((r) => r.path.endsWith("/generate"));
  const sent = (generates[0]?.body as { attachments?: string[] } | undefined)?.attachments ?? [];
  Object.assign(row.measured, {
    uploaded_files: uploaded.length,
    generate_requests: generates.length,
    attachments_in_job: sent.join(", "),
  });
  expect(uploaded).toHaveLength(3);
  expect(generates).toHaveLength(1);
  expect(sent).toEqual(uploaded);
  row.note = "Upload, ingest and generate endpoints are mocked; the request shape follows docs/API.md.";
});

test("WP-4 example prompt chips fill the prompt box", async ({ page, row }) => {
  await new MockApi().install(page);
  await page.goto("/p/p1");
  const chips = page.getByLabel("Example prompts").getByRole("button");
  await expect(chips.first()).toBeVisible();
  const texts = await chips.allTextContents();
  let filled = 0;
  for (const [i, text] of texts.entries()) {
    await chips.nth(i).click();
    await expect(page.getByLabel("Describe the part")).toHaveValue(text);
    filled++;
  }
  Object.assign(row.measured, { chips: texts.length, filled });
  expect(texts.length).toBeGreaterThanOrEqual(4);
  await row.shot("chip-filled");
});

test("WP-5 navigation reaches every dashboard page and lists generations per project", async ({
  page,
  context,
  row,
}) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await context.route("**/docs", (r) =>
    r.fulfill({ contentType: "text/html", body: "<title>API docs</title><h1>API docs</h1>" }),
  );
  const nav = page.getByRole("navigation", { name: "Main" });
  const reached: string[] = [];
  const visit = async (name: string, path: RegExp, heading: string) => {
    await nav.getByRole("link", { name, exact: true }).click();
    await expect(page).toHaveURL(path);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await row.shot(`${reached.length + 1}-${name.toLowerCase()}`);
    reached.push(name);
  };

  await page.goto("/help");
  await visit("Projects", /\/$/, "Projects");
  await visit("Library", /\/library$/, "Library");
  await visit("Settings", /\/settings$/, "Settings");
  await page.getByLabel("Dark").check();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByLabel("Light").check();
  await visit("Help", /\/help$/, "Help");

  await nav.getByRole("link", { name: "Projects" }).click();
  await page.getByRole("link", { name: "Bracket lab" }).click();
  await expect(page).toHaveURL(/\/p\/p1$/);
  const generations = await page
    .getByRole("list", { name: "Models" })
    .getByRole("listitem")
    .allTextContents();
  await row.shot(`${reached.length + 1}-project-models`);
  reached.push("Project models");
  await page.getByRole("navigation", { name: "Project" }).getByRole("link", { name: "Context" }).click();
  await expect(page.getByRole("table", { name: "Context files" })).toBeVisible();
  await row.shot(`${reached.length + 1}-context`);
  reached.push("Context manager");

  const [popup] = await Promise.all([
    page.waitForEvent("popup"),
    nav.getByRole("link", { name: "API", exact: true }).click(),
  ]);
  await expect(popup).toHaveURL(/\/docs$/);
  reached.push("API docs");
  await popup.close();

  Object.assign(row.measured, { pages: reached.join(", "), project_generations: generations.length });
  expect(generations).toHaveLength(1);
  expect(generations[0]).toContain("Sensor plate");
  row.note = "The API docs page is served by apps/api at /docs; the test stubs it.";
});

test("WP-9 library lists every part with thumbnail and title, newest first", async ({ page, row }) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await page.goto("/library");
  const expected = [...api.models, ...shopModels]
    .sort((a, b) => b.created.localeCompare(a.created))
    .map((m) => m.title);
  const cards = page.getByRole("list", { name: "Models" }).getByRole("listitem");
  await expect(cards.locator(".card-title")).toHaveText(expected);
  const imgs = cards.locator("img");
  await expect
    .poll(() => imgs.evaluateAll((all: HTMLImageElement[]) => all.every((i) => i.naturalWidth > 0)))
    .toBe(true);
  Object.assign(row.measured, {
    parts: expected.length,
    projects: 2,
    order: expected.join(" > "),
    thumbnails_loaded: await imgs.count(),
  });
  await row.shot("library");
});
