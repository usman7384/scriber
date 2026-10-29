import type { Page } from "@playwright/test";

type Seen = Record<string, number[]>;

// Samples every <progress> each animation frame and keeps the distinct values per aria-label, in order.
export const watchProgress = (page: Page) =>
  page.evaluate(() => {
    const seen: Seen = {};
    Object.assign(window, { seenProgress: seen });
    const tick = () => {
      document.querySelectorAll("progress").forEach((el) => {
        const list = (seen[el.getAttribute("aria-label") ?? ""] ??= []);
        if (list.at(-1) !== el.value) list.push(el.value);
      });
      requestAnimationFrame(tick);
    };
    tick();
  });

export const seenProgress = (page: Page) =>
  page.evaluate(() => (window as unknown as { seenProgress: Seen }).seenProgress);
