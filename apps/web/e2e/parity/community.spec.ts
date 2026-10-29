import { alicePart } from "../fixtures";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";

test("WP-10 community tab lists published parts, publishes from the editor and forks with provenance", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await page.goto("/m/m1");
  await expect(page.getByLabel("Bounding box")).toBeVisible();
  await page.getByRole("button", { name: "Publish" }).click();
  await expect(page.getByText("Published to the community")).toBeVisible();
  await row.shot("1-published");

  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Community" }).click();
  await expect(page).toHaveURL(/\/explore$/);
  const cards = page.getByRole("list", { name: "Published parts" }).getByRole("listitem");
  await expect(cards.locator(".card-title")).toHaveText(["Sensor plate", "Edge test plate"]);
  const widths = () =>
    cards.locator("img").evaluateAll((all: HTMLImageElement[]) => all.map((i) => i.naturalWidth));
  await expect.poll(async () => (await widths()).filter((w) => w > 0).length).toBe(2);
  const thumbs = await widths();
  const meta = await cards.locator("p").allTextContents();
  await row.shot("2-community");

  await page.getByLabel("Fork into project").selectOption({ label: "Bracket lab" });
  await page.getByRole("button", { name: "Fork Edge test plate" }).click();
  await expect(page.getByRole("status")).toHaveText("Forked Edge test plate into Bracket lab. Open the copy");
  await row.shot("3-forked");
  await page.getByRole("link", { name: "Open the copy" }).click();
  await expect(page).toHaveURL(/\/m\/m4$/);
  const provenance = page.getByText("Forked from Edge test plate v2 by alice");
  await expect(provenance).toBeVisible();
  await expect(page.getByLabel("Bounding box")).toHaveText("60.0 mm × 40.0 mm × 5.0 mm");
  await expect(page.getByLabel("Hole X", { exact: true })).toHaveValue("15");
  await row.shot("4-fork-in-editor");

  await page.getByRole("link", { name: "← Project" }).click();
  const forkCard = page
    .getByRole("list", { name: "Models" })
    .getByRole("listitem")
    .filter({ hasText: "Edge test plate" });
  await expect(forkCard).toContainText("Forked from Edge test plate v2 by alice");
  await row.shot("5-fork-in-project");

  const sent = (method: string, path: RegExp) =>
    api.requests.filter((r) => r.method === method && path.test(r.path));
  const [publish] = sent("POST", /^\/community$/);
  const [fork] = sent("POST", /\/fork$/);
  const copy = api.forks[0];
  Object.assign(row.measured, {
    publish_request: JSON.stringify(publish?.body),
    listed: meta.join(" | "),
    thumbnail_widths_px: thumbs.join(", "),
    fork_request: `${fork?.path} ${JSON.stringify(fork?.body)}`,
    forked_from: JSON.stringify(copy?.model.forked_from),
    fork_version: `${copy?.version.origin} v${copy?.version.number}: ${copy?.version.prompt}`,
    project_card: (await forkCard.textContent()) ?? "",
  });
  expect(publish?.body).toEqual({ model_id: "m1", version: 1 });
  expect(meta.map((m) => m.split(" · ").slice(0, 2).join(" · "))).toEqual(["v1 · by local", "v2 · by alice"]);
  expect(fork?.path).toBe(`/community/${alicePart.publication.id}/fork`);
  expect(fork?.body).toEqual({ project_id: "p1" });
  expect(copy?.model.forked_from).toEqual({
    publication: alicePart.publication.id,
    model_id: "m2",
    version: 2,
    title: "Edge test plate",
    author: "alice",
  });
  row.note =
    "Community page /explore over GET /community and POST /community/{id}/fork, Publish in the editor; routes mocked in the apps/api shape (routes/community.py). The API half (alice publishes, bob forks, original unchanged) is parity-20261029-052939.";
});
