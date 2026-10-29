import type { Param, Version } from "../api";

export interface Change {
  name: string;
  label: string;
  unit: string;
  from?: number | undefined;
  to?: number | undefined;
}

export const fixed = (n: number | undefined) => (n === undefined ? "—" : n.toFixed(2));

export const changeText = (c: Change) => `${c.label} ${fixed(c.from)} → ${fixed(c.to)} ${c.unit}`.trim();

export function paramDiff(before: Param[], after: Param[]): Change[] {
  const old = new Map(before.map((p) => [p.name, p]));
  const changed = after.flatMap((p): Change[] =>
    old.get(p.name)?.value === p.value
      ? []
      : [{ name: p.name, label: p.label, unit: p.unit, from: old.get(p.name)?.value, to: p.value }],
  );
  const now = new Set(after.map((p) => p.name));
  const dropped = before.flatMap((p): Change[] =>
    now.has(p.name) ? [] : [{ name: p.name, label: p.label, unit: p.unit, from: p.value }],
  );
  return [...changed, ...dropped];
}

export function proposedChanges(change: Record<string, number>, params: Param[]): Change[] {
  return Object.entries(change).map(([name, to]) => {
    const p = params.find((x) => x.name === name);
    return { name, label: p?.label ?? name, unit: p?.unit ?? "", from: p?.value, to };
  });
}

export const versionBefore = (versions: Version[], n: number) => versions.filter((v) => v.number < n).at(-1);
