import { enabled, groups, type Action, type ActionContext, type ActionGroup } from "../actions";

export interface Assignment {
  name: string;
  value: number;
}

export interface Row {
  action: Action;
  label: string;
  // Set for a parameter row built from "name = value".
  value?: number;
}

export interface Section {
  group: ActionGroup | "recent";
  rows: Row[];
}

// Higher is better; undefined is no match. A substring beats a scattered subsequence.
export const score = (query: string, text: string): number | undefined => {
  const q = query.trim().toLowerCase();
  const s = text.toLowerCase();
  if (!q) return 0;
  const at = s.indexOf(q);
  if (at >= 0) return 1000 - at;
  let last = -1;
  let gaps = 0;
  for (const ch of q.replace(/\s+/g, "")) {
    const next = s.indexOf(ch, last + 1);
    if (next < 0) return undefined;
    gaps += next - last - 1;
    last = next;
  }
  return 500 - gaps;
};

export const parseAssignment = (query: string): Assignment | undefined => {
  const m = /^\s*([^=]*[^=\s])\s*=\s*(-?\d+(?:[.,]\d+)?)\s*[a-zµ°]*\s*$/i.exec(query);
  if (!m?.[1] || !m[2]) return undefined;
  return { name: m[1], value: Number(m[2].replace(",", ".")) };
};

export const outOfBounds = (param: NonNullable<Action["param"]>, value: number) =>
  (param.min != null && value < param.min) || (param.max != null && value > param.max);

const best = (...scores: (number | undefined)[]) => {
  const found = scores.filter((s) => s !== undefined);
  return found.length ? Math.max(...found) : undefined;
};

export function rank(
  actions: readonly Action[],
  query: string,
  ctx: ActionContext,
  labelOf: (action: Action) => string,
  recent: readonly string[],
): Section[] {
  const q = query.trim();
  const assignment = parseAssignment(q);
  const live = actions.filter((a) => enabled(a, ctx));
  const recentRows = q ? [] : recent.flatMap((id) => live.filter((a) => a.id === id && a.group !== "agent"));
  const scored = live.flatMap((action): (Row & { score: number })[] => {
    if (recentRows.includes(action)) return [];
    const label = labelOf(action);
    if (action.group === "agent") return q ? [{ action, label, score: 0 }] : [];
    if (assignment && action.param) {
      const s = best(score(assignment.name, action.param.label), score(assignment.name, action.param.name));
      return s === undefined ? [] : [{ action, label, score: s, value: assignment.value }];
    }
    const s = score(q, `${label} ${action.hint ?? ""}`);
    return s === undefined ? [] : [{ action, label, score: s }];
  });
  const sections: Section[] = groups.map((group) => ({
    group,
    rows: scored
      .filter((r) => r.action.group === group)
      .sort((a, b) => b.score - a.score)
      .map(({ action, label, value }) => ({ action, label, value })),
  }));
  const recentSection: Section = {
    group: "recent",
    rows: recentRows.map((action) => ({ action, label: labelOf(action) })),
  };
  return [recentSection, ...sections].filter((s) => s.rows.length > 0);
}

export const remember = (recent: readonly string[], id: string, keep = 5) =>
  [id, ...recent.filter((r) => r !== id)].slice(0, keep);
