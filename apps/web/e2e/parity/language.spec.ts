import type { Page } from "@playwright/test";
import { messages, type Lang } from "../../src/i18n";
import { MockApi } from "../mock-api";
import { expect, test } from "./row";

// Every fixed string of a table, in the same order for both languages; functions are dynamic and skipped.
const leaves = (node: unknown): string[] =>
  typeof node === "string"
    ? [node]
    : typeof node === "object" && node !== null
      ? Object.values(node).flatMap(leaves)
      : [];

const en = leaves(messages.en);
const de = leaves(messages.de);
// Strings that change with the language; an English one that is also German text somewhere is left out.
const pairs = en.flatMap((s, i) => (s !== de[i] && !de.includes(s) ? [[s, de[i] ?? ""] as const] : []));
const englishOnly = new Set(pairs.map(([s]) => s));

// All text nodes and labelling attributes in the page, hidden ones (dialogs, tooltips) included.
const strings = (page: Page) =>
  page.evaluate(() => {
    const found: string[] = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const text = n.textContent?.trim();
      if (text && !n.parentElement?.closest("script, style")) found.push(text);
    }
    for (const el of document.body.querySelectorAll("[aria-label], [placeholder], [title], [alt]"))
      for (const a of ["aria-label", "placeholder", "title", "alt"]) {
        const v = el.getAttribute(a)?.trim();
        if (v) found.push(v);
      }
    return found;
  });

async function tour(page: Page, row: { shot: (n: string) => Promise<void> }, lang: Lang) {
  const seen = new Map<string, Set<string>>();
  const grab = async (where: string) => {
    seen.set(where, new Set(await strings(page)));
    await row.shot(`${lang}-${where}`);
  };
  const t = messages[lang];
  for (const path of ["/", "/library", "/settings", "/help", "/nowhere"]) {
    await page.goto(path);
    await expect(page.locator("main")).not.toContainText(t.loading);
    await grab(path === "/" ? "projects" : path.slice(1));
  }
  await page.goto("/p/p1?context=f1");
  await page.getByLabel(t.prompt.label).fill("Sensor plate 120 x 80 x 6 mm with four M6 holes");
  await page.getByRole("button", { name: t.prompt.generate }).click();
  await expect(page.getByRole("link", { name: t.timeline.stl })).toBeVisible();
  await grab("project");

  await page.goto("/p/p1/context");
  await page.locator(".dropzone input[type=file]").setInputFiles({
    name: "notes-3.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Wall 3 mm\n"),
  });
  await expect(page.getByRole("list", { name: t.context.uploads })).toContainText(t.status.processed ?? "");
  await page.getByRole("button", { name: "notes.txt", exact: true }).click();
  await page.getByRole("button", { name: `${t.context.delete} hole-table.csv` }).click();
  await expect(page.getByRole("list", { name: t.context.facts })).toBeVisible();
  await grab("context");

  await page.goto("/m/m1");
  await expect(page.getByLabel(t.viewer.bbox)).toBeVisible();
  await page.locator("details.menu summary").click();
  await page.getByRole("button", { name: t.share.share }).click();
  await page.getByRole("button", { name: t.viewer.face }).click();
  await page.getByRole("list", { name: t.editor.components }).getByRole("button").click();
  await grab("editor");

  await page.goto("/shared/s1");
  await expect(page.getByLabel(t.viewer.bbox)).toBeVisible();
  await grab("shared");
  return seen;
}

const hits = (seen: Map<string, Set<string>>, wanted: Set<string>) =>
  new Map([...seen].map(([where, found]) => [where, [...found].filter((s) => wanted.has(s))]));

test("WP-13 language selector switches every UI label between EN and DE and persists", async ({
  page,
  row,
}) => {
  const api = new MockApi();
  api.seed();
  await api.install(page);
  await page.goto("/");
  await expect(page.getByLabel("Language")).toHaveValue("en");
  const english = await tour(page, row, "en");

  await page.goto("/");
  await page.getByLabel("Language").selectOption("de");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Projekte");
  await page.reload();
  const persisted = {
    select: await page.getByLabel("Sprache").inputValue(),
    html_lang: await page.locator("html").getAttribute("lang"),
    stored: await page.evaluate(() => localStorage.getItem("lang")),
  };
  const german = await tour(page, row, "de");

  const all = (m: Map<string, Set<string>>) => new Set([...m.values()].flatMap((found) => [...found]));
  const [inEnglish, inGerman] = [all(english), all(german)];
  const shownInEn = pairs.filter(([e]) => inEnglish.has(e));
  const missingInDe = shownInEn.filter(([, d]) => !inGerman.has(d));
  const enInDe = hits(german, englishOnly);
  const untranslated = [...new Set([...enInDe.values()].flat())];
  Object.assign(row.measured, {
    table_strings: en.length,
    language_dependent_strings: pairs.length,
    shown_in_en_tour: shownInEn.length,
    their_german_shown_in_de_tour: shownInEn.length - missingInDe.length,
    english_left_in_de_tour: untranslated.length,
    untranslated: untranslated.join(" | "),
    persisted: JSON.stringify(persisted),
    pages: [...german.keys()].join(", "),
  });
  for (const [where, found] of enInDe) expect(found, `English left on ${where}`).toEqual([]);
  expect(missingInDe).toEqual([]);
  expect(persisted).toEqual({ select: "de", html_lang: "de", stored: "de" });
  row.note =
    "Own typed message table (src/i18n.ts, DE typed as EN so no key can be missing). The check walks every text node and aria-label, placeholder, title and alt on nine pages, hidden dialogs and tooltips included. API content (titles, findings, file names, example prompts) is not translated.";
});
