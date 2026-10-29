import { BoxGeometry, Box3, Group, Mesh, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import {
  bounds,
  boxDimensions,
  cadParts,
  fitDistance,
  fitZoom,
  frameOffset,
  gridStep,
  viewPose,
} from "./scene";

const plate = new Box3(new Vector3(-60, -40, 0), new Vector3(60, 40, 6));

it("converts a glTF part (metres, Y up) back to CAD millimetres with Z up", () => {
  const root = new Group();
  root.rotation.x = -Math.PI / 2;
  const mesh = new Mesh(new BoxGeometry(0.12, 0.08, 0.006).translate(0, 0, 0.003));
  mesh.userData.name = "plate";
  root.add(mesh);
  const parts = cadParts(root);
  expect(parts.map((p) => p.name)).toEqual(["plate"]);
  const box = bounds(parts);
  const size = box.getSize(new Vector3());
  expect([size.x, size.y, size.z].map((v) => +v.toFixed(6))).toEqual([120, 80, 6]);
  expect(box.min.z).toBeCloseTo(0);
});

it("places the camera for each standard view", () => {
  const dir = (view: Parameters<typeof viewPose>[0]) => {
    const { position, target } = viewPose(view, plate, 300);
    expect(position.distanceTo(target)).toBeCloseTo(300);
    return position.sub(target).normalize();
  };
  expect(dir("top").z).toBeCloseTo(1);
  expect(dir("front").y).toBeCloseTo(-1);
  expect(dir("right").x).toBeCloseTo(1);
  const iso = dir("iso");
  expect(iso.x).toBeGreaterThan(0);
  expect(iso.y).toBeLessThan(0);
  expect(iso.z).toBeGreaterThan(0);
  expect(viewPose("top", plate, 300).target.toArray()).toEqual([0, 0, 3]);
});

describe("framing in the free area", () => {
  const free = { left: 248, top: 100, width: 684, height: 680 };

  it("centres the projection on the free frame", () => {
    expect(frameOffset({ width: 1280, height: 900 }, free)).toEqual([50, 10]);
    expect(frameOffset({ width: 400, height: 300 }, { left: 0, top: 0, width: 400, height: 300 })).toEqual([
      0, 0,
    ]);
  });

  it("backs off and zooms out as the free frame shrinks", () => {
    const small = { ...free, width: 300 };
    expect(fitDistance(plate, small, 900, 35)).toBeGreaterThan(fitDistance(plate, free, 900, 35));
    expect(fitZoom(plate, small)).toBeLessThan(fitZoom(plate, free));
    // the bounding sphere (radius ~72 mm) fits the 680 px frame with a margin
    expect(fitZoom(plate, free) * 2 * 72.2).toBeLessThan(680);
  });
});

it("picks a grid step of 1, 10 or 100 mm from the part size", () => {
  expect(gridStep(new Box3(new Vector3(0, 0, 0), new Vector3(20, 10, 5)))).toBe(1);
  expect(gridStep(plate)).toBe(10);
  expect(gridStep(new Box3(new Vector3(0, 0, 0), new Vector3(2000, 1000, 50)))).toBe(100);
});

it("draws L, W and H dimensions outside the box with their true lengths", () => {
  const dims = boxDimensions(plate);
  expect(dims.map((d) => +d.value.toFixed(6))).toEqual([120, 80, 6]);
  const [l, w, h] = dims.map((d) => d.at.toArray().map((v) => +v.toFixed(3)));
  expect(l?.[1]).toBeLessThan(-40);
  expect(w?.[0]).toBeGreaterThan(60);
  expect(h?.[2]).toBe(3);
  dims.forEach((d) => expect(d.segments).toHaveLength(10));
});
