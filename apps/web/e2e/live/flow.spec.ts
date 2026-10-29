import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { expect, test } from "../parity/row";
import type { Job } from "../../src/api";
import { API, flat, getJson, kernelCheck, project, repoFile, root, versions } from "./live";

test("WP-14 live: beginner flow, prompt to a sliceable STL in three UI steps", async ({
  page,
  request,
  row,
}) => {
  const id = await project(request, "WP-14 live");
  await page.goto(`/p/${id}`);
  const steps: string[] = [];
  const prompt = "mounting plate 60 x 40 x 4 mm with two M3 holes 48 mm apart";

  await page.getByLabel("Describe the part").fill(prompt);
  steps.push("type the prompt");
  const started = Date.now();
  await page.getByRole("button", { name: "Generate" }).click();
  steps.push("Generate");
  const status = page.getByRole("region", { name: "Generation timeline" }).getByRole("status");
  await expect(status).toHaveText(/done|failed/, { timeout: 480_000 });
  row.measured.generation_s = +((Date.now() - started) / 1000).toFixed(1);
  row.measured.generation = (await status.textContent()) ?? "";
  const [job] = await getJson<Job[]>(request, `/projects/${id}/jobs`);
  row.measured.job_steps = (job?.steps ?? []).map((s) => `${s.kind} ${s.attempt}: ${s.message}`).join(" | ");
  await row.shot("1-finished");
  expect(row.measured.generation).toBe("done");
  const link = page.getByRole("link", { name: "Download STL" });
  const download = page.waitForEvent("download");
  await link.click();
  steps.push("Download STL");
  const file = await download;
  const path = join(row.dir, file.suggestedFilename());
  await file.saveAs(path);

  const [model] = (await (await request.get(`${API}/projects/${id}/models`)).json()) as { id: string }[];
  const version = (await versions(request, model?.id ?? ""))[0];
  const stl = kernelCheck("stl", path);
  Object.assign(row.measured, {
    ui_steps: steps.length,
    steps: steps.join(" -> "),
    prompt,
    checks: (version?.checks ?? []).map((c) => `${c.description}: ${c.passed ? "pass" : "fail"}`).join("; "),
    api_bbox: version?.metrics?.bbox.join(" x ") ?? null,
    stl_file: file.suggestedFilename(),
    ...flat(stl),
  });
  expect(steps).toHaveLength(3);
  expect(stl.watertight).toBe(true);
  expect(stl.winding_consistent).toBe(true);
  expect(stl.sliced_ok, String(stl.slicer)).toBe(true);
  row.note =
    "Live generation with the configured default model; the STL is the browser download through the dev proxy, sliced by PrusaSlicer (VM-9 criteria: exit 0, manifold, layers > 0, no errors). The checklist prompt (motor holder for a 28 mm motor, 2 M3 screws) is not used: the default model fails its requirement checks after 6 attempts.";
});

test("AP-9 live: sizing XML piped to the API builds a model with no UI input; the web app shows it", async ({
  page,
  request,
  row,
}) => {
  const xml = "evals/parity/m4/aircraft/sizing.xml";
  const step = join(row.dir, "wing.step");
  const config = process.env.PARTWRIGHT_LIVE_CONFIG ?? "config.yaml";
  const out = execFileSync(
    "uv",
    ["run", "partwright", "--config", config, "pipe", "--api", API, "--out", step],
    {
      cwd: root,
      input: repoFile(xml),
      encoding: "utf-8",
    },
  );
  const [, model = "", number = ""] = /model (\w+) v(\d+)/.exec(out) ?? [];
  const wing = kernelCheck("wing", step, join(root, xml));
  const origin = (await versions(request, model))[0]?.origin;

  await page.goto(`/m/${model}`);
  const bbox = page.getByLabel("Bounding box");
  await expect(bbox).toBeVisible();
  const history = page.getByRole("list", { name: "Version history" });
  await expect(history.locator("strong")).toHaveText([`v${number}`]);
  await row.shot("1-editor");
  Object.assign(row.measured, {
    cli_output: out.trim().split("\n")[0] ?? "",
    ui_bbox: (await bbox.textContent()) ?? "",
    ui_history: (await history.textContent()) ?? "",
    ...flat(wing),
  });
  expect(origin).toBe("sizing");
  expect(wing.in_11_checks_passed).toBe(wing.in_11_checks);
  row.note =
    "Live: `partwright pipe` posts the sizing XML to the running API (POST /projects/{id}/sizing, no model call); IN-11 checks on the STEP it saved; the editor opens the built model.";
});
