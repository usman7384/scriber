import { Box3, Vector3 } from "three";
import type { Vec3 } from "../api";

export interface ExplodePart {
  name: string;
  parent?: string | undefined;
  axis?: Vec3 | null | undefined;
  box: Box3;
}

const GAP = 0.15;
const SPREAD = 0.5;

const extentAlong = (box: Box3, a: Vector3) => {
  const s = box.getSize(new Vector3());
  return Math.abs(s.x * a.x) + Math.abs(s.y * a.y) + Math.abs(s.z * a.z);
};

// Where each part sits when exploded by t (0 assembled, 1 fully apart). A mated part slides along its joint
// axis, away from its parent, by its own depth plus a gap; children carry their parent's offset with them.
// Parts with no joint spread out from the assembly's centre, except the largest, which stays put.
export function explodeOffsets(parts: ExplodePart[], t: number): Map<string, Vector3> {
  const byName = new Map(parts.map((p) => [p.name, p]));
  const all = parts.reduce((b, p) => b.union(p.box), new Box3());
  const centre = all.getCenter(new Vector3());
  const reach = Math.max(all.getSize(new Vector3()).length() / 2, 1);
  const loose = parts.filter((p) => !p.axis || !p.parent || !byName.has(p.parent));
  const anchor = loose.reduce<ExplodePart | undefined>(
    (big, p) => (!big || volume(p.box) > volume(big.box) ? p : big),
    undefined,
  );
  const out = new Map<string, Vector3>();
  const place = (p: ExplodePart): Vector3 => {
    const done = out.get(p.name);
    if (done) return done;
    const parent = p.parent ? byName.get(p.parent) : undefined;
    let offset: Vector3;
    if (p.axis && parent) {
      const axis = new Vector3(...p.axis).normalize();
      const away = p.box.getCenter(new Vector3()).sub(parent.box.getCenter(new Vector3())).dot(axis);
      if (away < -1e-6 * reach) axis.negate();
      offset = place(parent)
        .clone()
        .addScaledVector(axis, t * (extentAlong(p.box, axis) + GAP * reach));
    } else if (p === anchor) {
      offset = new Vector3();
    } else {
      const from = p.box.getCenter(new Vector3()).sub(centre);
      const dir = from.lengthSq() > 1e-12 ? from.normalize() : new Vector3(0, 0, 1);
      offset = dir.multiplyScalar(t * SPREAD * reach);
    }
    out.set(p.name, offset);
    return offset;
  };
  parts.forEach(place);
  return out;
}

const volume = (b: Box3) => {
  const s = b.getSize(new Vector3());
  return s.x * s.y * s.z;
};
