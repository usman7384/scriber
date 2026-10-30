import { expect, it } from "vitest";
import { lattice, turn } from "./globe";

const length = (p: number[]) => Math.hypot(...p);

it("puts every lattice point on the unit sphere and keeps it there when turned", () => {
  const points = lattice(200);
  expect(points).toHaveLength(200);
  for (const p of points) {
    expect(length(p)).toBeCloseTo(1, 9);
    expect(length(turn(p, 1.3))).toBeCloseTo(1, 9);
  }
});
