import { describe, expect, it } from "vitest";
import { splitQuantities } from "./quantities";

const found = (text: string) => splitQuantities(text).flatMap((s) => (s.quantity ? [s.text] : []));

describe("splitQuantities", () => {
  it("finds lengths, threads, diameters and dimension chains", () => {
    expect(found("Plate 120 x 80 x 6 mm with four M6 holes, Ø12 bore")).toEqual([
      "120 x 80 x 6 mm",
      "M6",
      "Ø12",
    ]);
    expect(found("motor holder for 28 mm motor, 2 M3 screws")).toEqual(["28 mm", "M3"]);
    expect(found("wall 2.5mm, tolerance ± 0.1 mm, angle 45°, M4x0.7")).toEqual([
      "2.5mm",
      "± 0.1 mm",
      "45°",
      "M4x0.7",
    ]);
  });

  it("leaves bare numbers and words that start with a unit alone", () => {
    expect(found("4 mounting tabs and 2 Nuts")).toEqual([]);
    expect(found("Mounting plate")).toEqual([]);
  });

  it("keeps every character, in order", () => {
    const text = "Spacer ring, 30 mm outer diameter, 12 mm bore";
    expect(
      splitQuantities(text)
        .map((s) => s.text)
        .join(""),
    ).toBe(text);
  });
});
