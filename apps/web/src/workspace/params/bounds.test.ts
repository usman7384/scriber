import { expect, it } from "vitest";
import { param } from "../../test-utils";
import { keyStep, outOfBounds, sliderRange } from "./bounds";

it("uses the declared bounds for the slider, or a span around the value", () => {
  expect(sliderRange(param({ min: 3, max: 20, value: 6 }))).toEqual([3, 20]);
  expect(sliderRange(param({ value: 120 }))).toEqual([0, 240]);
  expect(sliderRange(param({ value: -4 }))).toEqual([-8, 0]);
});

it("steps a tenth of the span's magnitude, ten times with Shift, a tenth with Alt", () => {
  const plain = { shiftKey: false, altKey: false };
  expect(keyStep([3, 20], plain)).toBe(1);
  expect(keyStep([0, 240], plain)).toBe(10);
  expect(keyStep([3, 20], { ...plain, shiftKey: true })).toBe(10);
  expect(keyStep([3, 20], { ...plain, altKey: true })).toBeCloseTo(0.1);
});

it("names the bound a value crosses", () => {
  const p = param({ min: 3, max: 20 });
  expect(outOfBounds(p, 2)).toEqual({ side: "below", limit: 3 });
  expect(outOfBounds(p, 21)).toEqual({ side: "above", limit: 20 });
  expect(outOfBounds(p, 20)).toBeUndefined();
  expect(outOfBounds(param(), 1e9)).toBeUndefined();
});
