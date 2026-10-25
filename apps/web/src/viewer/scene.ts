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

export function viewPose(view: View, box: Box3) {
  const target = box.getCenter(new Vector3());
  const size = box.getSize(new Vector3());
  const distance = Math.max(size.x, size.y, size.z, 10) * 2.5;
  return { target, position: directions[view].clone().normalize().multiplyScalar(distance).add(target) };
}
