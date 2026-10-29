import type { Version } from "../api";

export interface Tally {
  pass: number;
  warn: number;
  fail: number;
  assumed: number;
}

// Requirement checks and findings counted for the checks pill; `default` parameters are the agent's assumptions.
export function tally({ checks, findings, params }: Pick<Version, "checks" | "findings" | "params">): Tally {
  const errors = findings.filter((f) => f.severity === "error").length;
  return {
    pass: checks.filter((c) => c.passed).length,
    warn: findings.length - errors,
    fail: checks.filter((c) => !c.passed).length + errors,
    assumed: params.filter((p) => p.provenance.source === "default").length,
  };
}
