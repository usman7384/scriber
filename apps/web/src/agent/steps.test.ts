import { describe, expect, it } from "vitest";
import type { Step } from "../api";
import { param, version } from "../test-utils";
import { changeText, paramDiff, proposedChanges } from "./diff";
import { ago, byAgent, stepStates } from "./steps";

const step = (kind: string): Step => ({ kind, message: "", attempt: 1, elapsed_ms: 0 });

describe("stepStates", () => {
  it("reads a check followed by a repair as failed and the rest as passed", () => {
    const steps = ["requirements", "emit", "check", "repair", "check"].map(step);
    expect(stepStates(steps)).toEqual(["pass", "pass", "fail", "pass", "run"]);
    expect(stepStates(steps, "done")).toEqual(["pass", "pass", "fail", "pass", "pass"]);
    expect(stepStates(steps, "failed").at(-1)).toBe("fail");
    expect(stepStates(steps.slice(0, 2))).toEqual(["pass", "pass"]);
  });
});

describe("paramDiff", () => {
  it("lists changed and dropped parameters with both values", () => {
    const before = [param(), param({ name: "hole", label: "Hole", value: 6.6 })];
    const after = [param({ value: 130 })];
    expect(paramDiff(before, after).map(changeText)).toEqual([
      "Plate Length 120.00 → 130.00 mm",
      "Hole 6.60 → — mm",
    ]);
    expect(paramDiff(after, after)).toEqual([]);
  });

  it("states a proposal against the current values", () => {
    expect(proposedChanges({ plate_length: 140, extra: 2 }, [param()]).map(changeText)).toEqual([
      "Plate Length 120.00 → 140.00 mm",
      "extra — → 2.00",
    ]);
  });
});

it("tells agent versions from user versions", () => {
  expect(byAgent(version(1))).toBe(true);
  expect(byAgent(version(2, { origin: "params" }))).toBe(false);
  expect(byAgent(version(3, { origin: "suggestion" }))).toBe(true);
});

it("says how long ago in the chosen language", () => {
  const now = Date.parse("2026-10-29T12:00:00Z");
  expect(ago("2026-10-29T11:58:00Z", "en", now)).toBe("2 minutes ago");
  expect(ago("2026-10-28T12:00:00Z", "de", now)).toBe("gestern");
});
