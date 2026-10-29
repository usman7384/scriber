import { useMemo, useSyncExternalStore } from "react";
import { Color, SRGBColorSpace } from "three";

export interface Tint {
  rgb: [number, number, number];
  alpha: number;
}

const hex = /^#([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i;
const fn = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)\s*(?:[/,]\s*([\d.]+)(%?))?\s*\)$/i;

// Tokens are six-digit hex or functional rgb with an optional alpha; three.js wants channels and alpha apart.
export function parseColor(css: string): Tint {
  const h = hex.exec(css.trim());
  if (h) return { rgb: [h[1], h[2], h[3]].map((c) => parseInt(c ?? "0", 16)) as Tint["rgb"], alpha: 1 };
  const m = fn.exec(css.trim());
  if (!m) throw new Error(`unsupported colour token: ${css}`);
  const alpha = m[4] === undefined ? 1 : Number(m[4]) / (m[5] ? 100 : 1);
  return { rgb: [Number(m[1]), Number(m[2]), Number(m[3])], alpha };
}

export const toColor = ({ rgb }: Tint) =>
  new Color().setRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, SRGBColorSpace);

const names = [
  "part",
  "part-edge",
  "accent",
  "faint",
  "grid-minor",
  "grid-major",
  "axis-x",
  "axis-y",
  "axis-z",
] as const;

export type Palette = Record<(typeof names)[number], Tint>;

const read = () => {
  const style = getComputedStyle(document.documentElement);
  return names.map((n) => style.getPropertyValue(`--${n}`)).join("|");
};

const subscribe = (changed: () => void) => {
  const observer = new MutationObserver(changed);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
};

// Viewer colours from tokens.css, re-read whenever the theme changes.
export function usePalette(): Palette {
  const raw = useSyncExternalStore(subscribe, read);
  return useMemo(
    () => Object.fromEntries(raw.split("|").map((v, i) => [names[i], parseColor(v)])) as Palette,
    [raw],
  );
}
