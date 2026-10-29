import type { Job, Step, Version } from "../api";

export type StepState = "pass" | "fail" | "run";

// Without Step.detail a check's verdict is read from what follows it: a repair means it failed.
export function stepStates(steps: Step[], end?: Job["status"]): StepState[] {
  return steps.map((s, i) => {
    const next = steps[i + 1];
    if (s.kind === "failed") return "fail";
    if (s.kind === "check" && next) return next.kind === "repair" ? "fail" : "pass";
    if (next) return "pass";
    // A step is sent when it finishes, so only a trailing check still waits for its verdict.
    if (!end) return s.kind === "check" ? "run" : "pass";
    return end === "failed" ? "fail" : "pass";
  });
}

const agentOrigins: Version["origin"][] = ["generate", "refine", "suggestion", "variant", "context"];

export const byAgent = (v: Version) => agentOrigins.includes(v.origin);

const units: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31_536_000],
  ["month", 2_592_000],
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

export function ago(iso: string, lang: string, now = Date.now()) {
  const s = Math.round((Date.parse(iso) - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
  const [unit, size] = units.find(([, size]) => Math.abs(s) >= size) ?? ["second", 1];
  return rtf.format(Math.round(s / size), unit);
}
