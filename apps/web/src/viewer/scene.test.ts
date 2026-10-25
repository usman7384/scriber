import { BoxGeometry, Box3, Group, Mesh, Vector3 } from "three";
import { expect, it } from "vitest";
import { bounds, cadParts, viewPose } from "./scene";

it("converts a glTF part (metres, Y up) back to CAD millimetres with Z up", () => {
  const root = new Group();
  root.rotation.x = -Math.PI / 2;
  const plate = new Mesh(new BoxGeometry(0.12, 0.08, 0.006).translate(0, 0, 0.003));
  plate.userData.name = "plate";
  root.add(plate);
  const parts = cadParts(root);
  expect(parts.map((p) => p.name)).toEqual(["plate"]);
  const box = bounds(parts);
  const size = box.getSize(new Vector3());
  expect([size.x, size.y, size.z].map((v) => +v.toFixed(6))).toEqual([120, 80, 6]);
  expect(box.min.z).toBeCloseTo(0);
});

it("places the camera for each standard view", () => {
  const box = new Box3(new Vector3(-60, -40, 0), new Vector3(60, 40, 6));
  const dir = (view: Parameters<typeof viewPose>[0]) => {
    const { position, target } = viewPose(view, box);
    return position.sub(target).normalize();
  };
  expect(dir("top").z).toBeCloseTo(1);
  expect(dir("front").y).toBeCloseTo(-1);
  expect(dir("right").x).toBeCloseTo(1);
  const iso = dir("iso");
  expect(iso.x).toBeGreaterThan(0);
  expect(iso.y).toBeLessThan(0);
  expect(iso.z).toBeGreaterThan(0);
  expect(viewPose("top", box).target.toArray()).toEqual([0, 0, 3]);
});
