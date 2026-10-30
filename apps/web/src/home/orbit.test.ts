import { expect, it } from "vitest";
import { clamp, drift, range, stepFor, turnFor } from "./orbit";

it("spaces parts by arc length and turns by the scrolled distance", () => {
  expect(stepFor(100, 100)).toBeCloseTo(45);
  expect(turnFor(Math.PI * 100, 100)).toBeCloseTo(-180);
});

it("lets the horizon turn from the newest part to the oldest and no further", () => {
  expect(range(5, 10)).toEqual([-45, 5]);
  expect(range(0, 10)).toEqual([-5, 5]);
  expect(clamp(-90, range(5, 10))).toBe(-45);
  expect(clamp(20, range(5, 10))).toBe(5);
});

it("drifts slowly and reverses at either end", () => {
  expect(drift(0, -1, 2, [-10, 5])).toEqual({ spin: -2, velocity: -1 });
  expect(drift(-9, -1, 2, [-10, 5])).toEqual({ spin: -10, velocity: 1 });
  expect(drift(4, 1, 2, [-10, 5])).toEqual({ spin: 5, velocity: -1 });
});
