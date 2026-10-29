import type { Param } from "../../api";

export function sliderRange(p: Param): [number, number] {
  const span = Math.abs(p.value) || 10;
  return [p.min ?? (p.value >= 0 ? Math.max(0, p.value - span) : p.value - span), p.max ?? p.value + span];
}

// One keyboard step: a round tenth of the slider span (Shift x10, Alt x0.1).
export function keyStep([lo, hi]: [number, number], e: { shiftKey: boolean; altKey: boolean }) {
  const base = 10 ** (Math.floor(Math.log10(Math.max(hi - lo, 1e-6))) - 1);
  return base * (e.shiftKey ? 10 : e.altKey ? 0.1 : 1);
}

export type Bound = { side: "below" | "above"; limit: number };

export function outOfBounds(p: Param, value: number): Bound | undefined {
  if (p.min != null && value < p.min) return { side: "below", limit: p.min };
  if (p.max != null && value > p.max) return { side: "above", limit: p.max };
  return undefined;
}

export const fixed = (value: number, unit: string) => `${value.toFixed(2)} ${unit}`;

export const numberOf = (draft: string) => (draft.trim() === "" ? NaN : Number(draft));
