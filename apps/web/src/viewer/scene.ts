import { Box3, Matrix4, Vector3, type BufferGeometry, type Mesh, type Object3D } from "three";

export type View = "top" | "front" | "right" | "iso";

export interface CadPart {
  name: string;
  geometry: BufferGeometry;
}

// The CAD exporter writes glTF in metres and rotates Z-up to Y-up; undo both so the scene is CAD mm, Z up.
const gltfToCad = new Matrix4()
  .makeScale(1000, 1000, 1000)
  .multiply(new Matrix4().makeRotationX(Math.PI / 2));

export function cadParts(root: Object3D): CadPart[] {
  root.updateMatrixWorld(true);
  const parts: CadPart[] = [];
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    const geometry = mesh.geometry
      .clone()
      .applyMatrix4(new Matrix4().multiplyMatrices(gltfToCad, mesh.matrixWorld));
    geometry.computeBoundingBox();
    parts.push({ name: nodeName(mesh), geometry });
  });
  return parts;
}

// glTF primitives become unnamed child meshes; the part is the nearest glTF node (GLTFLoader keeps its name in userData).
function nodeName(o: Object3D): string {
  for (let x: Object3D | null = o; x; x = x.parent) {
    if (typeof x.userData.name === "string") return x.userData.name;
  }
  return o.name || "part";
}

export function bounds(parts: CadPart[]): Box3 {
  const box = new Box3();
  parts.forEach((p) => p.geometry.boundingBox && box.union(p.geometry.boundingBox));
  return box;
}

const directions: Record<View, Vector3> = {
  top: new Vector3(0, -1e-4, 1),
  front: new Vector3(0, -1, 0),
  right: new Vector3(1, 0, 0),
  iso: new Vector3(1, -1, 0.8),
};

export const isOrtho = (view: View) => view !== "iso";

export function viewPose(view: View, box: Box3, distance: number) {
  const target = box.getCenter(new Vector3());
  return { target, position: directions[view].clone().normalize().multiplyScalar(distance).add(target) };
}

// The part of the canvas not covered by floating panels, in canvas pixels.
export interface Frame {
  left: number;
  top: number;
  width: number;
  height: number;
}

const margin = 1.15;

export const radius = (box: Box3) => Math.max(box.getSize(new Vector3()).length() / 2, 5);

// Distance at which a perspective camera shows the part's bounding sphere inside the free frame.
export function fitDistance(box: Box3, free: Frame, canvasHeight: number, fovDeg: number) {
  const span = Math.max(Math.min(free.width, free.height) / canvasHeight, 0.1);
  return (margin * radius(box)) / (Math.tan((fovDeg * Math.PI) / 360) * span);
}

// Pixels per mm for an orthographic camera showing the same sphere.
export const fitZoom = (box: Box3, free: Frame) =>
  Math.max(Math.min(free.width, free.height), 40) / (2 * margin * radius(box));

// setViewOffset shift that puts the projection centre in the middle of the free frame.
export const frameOffset = (canvas: { width: number; height: number }, free: Frame): [number, number] => [
  canvas.width / 2 - (free.left + free.width / 2),
  canvas.height / 2 - (free.top + free.height / 2),
];

// Minor grid step from 1 / 10 / 100 mm, so minor lines stay at least ~8 px apart at the fitted zoom.
export const gridStep = (box: Box3) => [1, 10, 100].find((s) => s >= radius(box) / 35) ?? 100;

export interface Dimension {
  axis: 0 | 1 | 2;
  value: number;
  segments: Vector3[];
  at: Vector3;
}

// Drafting-style dimensions of the box: extension lines, a dimension line with slash ticks, the chip at its middle.
export function boxDimensions(box: Box3): Dimension[] {
  const { min, max } = box;
  const size = box.getSize(new Vector3());
  const offset = Math.max(size.x, size.y, size.z) * 0.14;
  const tick = offset * 0.12;
  const corner = new Vector3(max.x, min.y, min.z);
  const dimension = (axis: 0 | 1 | 2, a: Vector3, b: Vector3, out: Vector3): Dimension => {
    const slash = b.clone().sub(a).normalize().add(out).multiplyScalar(tick);
    const [a2, b2] = [a, b].map((p) => p.clone().addScaledVector(out, offset)) as [Vector3, Vector3];
    const extension = (p: Vector3, q: Vector3) => [
      p.clone().addScaledVector(out, tick),
      q.clone().addScaledVector(out, tick),
    ];
    const ticks = (p: Vector3) => [p.clone().sub(slash), p.clone().add(slash)];
    return {
      axis,
      value: a.distanceTo(b),
      segments: [...extension(a, a2), ...extension(b, b2), a2, b2, ...ticks(a2), ...ticks(b2)],
      at: a2.clone().lerp(b2, 0.5),
    };
  };
  return [
    dimension(0, new Vector3(min.x, min.y, min.z), corner, new Vector3(0, -1, 0)),
    dimension(1, corner, new Vector3(max.x, max.y, min.z), new Vector3(1, 0, 0)),
    dimension(2, corner, new Vector3(max.x, min.y, max.z), new Vector3(1, -1, 0).normalize()),
  ];
}
