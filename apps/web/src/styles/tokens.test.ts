import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";

const src = join(__dirname, "..");
const colour = /#[0-9a-f]{3,8}\b|\b(rgba?|hsla?)\(/i;

// Screens not yet moved onto tokens; each package deletes its entry when it does.
const legacy = [
  "styles/tokens.css",
  "styles/app.css",
  "context/GraphPanel.tsx",
  "viewer/Measurements.tsx",
  "viewer/Model.tsx",
];

it("keeps colour literals in tokens.css only", () => {
  const files = readdirSync(src, { recursive: true, encoding: "utf8" })
    .map((path) => path.replaceAll("\\", "/"))
    .filter((path) => /\.(tsx?|css)$/.test(path) && !/\.test\.tsx?$/.test(path));
  expect(files).toContain("styles/tokens.css");
  const offenders = files.filter(
    (path) => !legacy.includes(path) && colour.test(readFileSync(join(src, path), "utf8")),
  );
  expect(offenders).toEqual([]);
});
