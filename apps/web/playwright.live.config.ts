import { mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig } from "@playwright/test";
import base from "./playwright.parity.config";

const root = join(import.meta.dirname, "..", "..");
const webPort = 5198;
const apiPort = 8765;

// Runner process only: workers inherit the env, so the stack and the evidence folder are set up once.
if (!process.env.SCRIBER_LIVE_CONFIG) {
  for (const old of readdirSync(tmpdir()).filter((n) => n.startsWith("scriber-live-")))
    rmSync(join(tmpdir(), old), { recursive: true, force: true });
  const dir = mkdtempSync(join(tmpdir(), "scriber-live-"));
  const config = readFileSync(join(root, "config.yaml"), "utf-8")
    .replace(/^data_dir:.*$/m, `data_dir: ${join(dir, "data").replaceAll("\\", "/")}`)
    .replace(/^output_dir:.*$/m, `output_dir: ${join(dir, "out").replaceAll("\\", "/")}`)
    .replace(/^(\s+port:) \d+$/m, `$1 ${apiPort}`);
  writeFileSync(join(dir, "config.yaml"), config);
  process.env.SCRIBER_LIVE_CONFIG = join(dir, "config.yaml");
  process.env.SCRIBER_LIVE_API = `http://127.0.0.1:${apiPort}`;
  process.env.PARITY_RUN = `live-${process.env.PARITY_RUN}`;
}

export default defineConfig({
  ...base,
  testDir: "e2e/live",
  workers: 1,
  timeout: 600_000,
  expect: { timeout: 60_000 },
  use: { ...base.use, baseURL: `http://127.0.0.1:${webPort}` },
  webServer: [
    {
      command: `uv run scriber --config "${process.env.SCRIBER_LIVE_CONFIG}" serve`,
      cwd: root,
      url: `${process.env.SCRIBER_LIVE_API}/health`,
      timeout: 180_000,
      reuseExistingServer: false,
      stdout: "pipe",
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${webPort} --strictPort`,
      url: `http://127.0.0.1:${webPort}`,
      env: { SCRIBER_API_URL: process.env.SCRIBER_LIVE_API ?? "" },
      reuseExistingServer: false,
    },
  ],
});
