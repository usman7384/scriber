import { Box3, Vector3 } from "three";
import { expect, it } from "vitest";
import { explodeOffsets, type ExplodePart } from "./explode";

const box = (min: [number, number, number], max: [number, number, number]) =>
  new Box3(new Vector3(...min), new Vector3(...max));

// A 40 mm plate with a 10 mm cube on top and a 4 mm pin in the cube, both mated along z.
const stack: ExplodePart[] = [
  { name: "plate", box: box([-20, -20, 0], [20, 20, 40]) },
  { name: "cube", parent: "plate", axis: [0, 0, 1], box: box([5, -5, 40], [15, 5, 50]) },
  { name: "pin", parent: "cube", axis: [0, 0, -1], box: box([8, -2, 50], [12, 2, 60]) },
];

it("keeps everything assembled at zero", () => {
  for (const offset of explodeOffsets(stack, 0).values()) expect(offset.length()).toBe(0);
});

it("slides mated parts away from their parent along the joint axis, children with them", () => {
  const offsets = explodeOffsets(stack, 1);
  const reach = box([-20, -20, 0], [20, 20, 60]).getSize(new Vector3()).length() / 2;
  expect(offsets.get("plate")?.toArray()).toEqual([0, 0, 0]);
  const cube = offsets.get("cube");
  expect(cube?.x).toBe(0);
  expect(cube?.z).toBeCloseTo(10 + 0.15 * reach);
  // the pin's axis points down into the cube, so it is turned to point away from it
  expect(offsets.get("pin")?.z).toBeCloseTo((cube?.z ?? 0) + 10 + 0.15 * reach);
});

it("spreads parts without joints from the centre and leaves the largest in place", () => {
  const loose: ExplodePart[] = [
    { name: "base", box: box([-50, -50, 0], [50, 50, 10]) },
    { name: "left", box: box([-40, -5, 10], [-30, 5, 20]) },
  ];
  const offsets = explodeOffsets(loose, 1);
  expect(offsets.get("base")?.length()).toBe(0);
  expect(offsets.get("left")?.x).toBeLessThan(0);
});
