import type { Process } from "./api";

export const processes: Record<Process, string> = {
  any: "Any process",
  milling_3axis: "3-axis milling",
  fdm: "FDM printing",
  sla: "SLA printing",
  sls: "SLS printing",
};

export const mm = (n: number) => `${n.toFixed(1)} mm`;

export const seconds = (ms: number) => `${(ms / 1000).toFixed(1)} s`;

export const date = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export const byNewest = <T extends { created: string }>(items: T[]) =>
  [...items].sort((a, b) => b.created.localeCompare(a.created));
