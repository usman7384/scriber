import { expect, it } from "vitest";
import type { Finding } from "../api";
import { param } from "../test-utils";
import { tally } from "./tally";

const finding = (severity: string): Finding => ({ rule_id: "r", severity, binding: "static", message: "m" });

it("counts passed and failed checks, warnings, errors and assumed parameters", () => {
  expect(
    tally({
      checks: [
        { description: "a", passed: true, actual: null },
        { description: "b", passed: false, actual: null },
      ],
      findings: [finding("warning"), finding("error"), finding("warning")],
      params: [param(), param({ provenance: { source: "default" } })],
    }),
  ).toEqual({ pass: 1, warn: 2, fail: 2, assumed: 1 });
});
