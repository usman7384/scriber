import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { stripVTControlCharacters } from "node:util";
import { fileURLToPath } from "node:url";
import { test as base } from "@playwright/test";

type Measured = Record<string, string | number | boolean | null>;

export interface Row {
  dir: string;
  measured: Measured;
  note: string;
  shot: (name: string) => Promise<void>;
}

const runDir = fileURLToPath(
  new URL(`../../../../evals/results/parity-web-${process.env.PARITY_RUN ?? "local"}/`, import.meta.url),
);

// Evidence has the shape of scriber_evals.parity.Evidence; passed is the Playwright verdict of the row's test.
export const test = base.extend<{ row: Row }>({
  row: async ({ page }, provide, info) => {
    const id = info.title.split(" ")[0] ?? info.title;
    const dir = join(runDir, id);
    mkdirSync(dir, { recursive: true });
    const row: Row = {
      dir,
      measured: {},
      note: "",
      shot: async (name) => {
        await page.screenshot({ path: join(dir, `${name}.png`) });
      },
    };
    await provide(row);
    await page.close();
    await page.video()?.saveAs(join(dir, "video.webm"));
    const passed = info.status === "passed";
    const error = stripVTControlCharacters(info.error?.message ?? "").split("\n")[0];
    const note = [row.note, passed ? "" : `failed: ${error}`].filter(Boolean).join(" ");
    const evidence = { row: id, passed, measured: row.measured, note };
    writeFileSync(join(dir, "evidence.json"), JSON.stringify(evidence, null, 2) + "\n");
  },
});

export { expect } from "@playwright/test";
