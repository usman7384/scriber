import { useMemo } from "react";
import { BufferAttribute, BufferGeometry, Vector3, type Box3 } from "three";
import { toColor, type Palette, type Tint } from "./palette";
import { gridStep, radius } from "./scene";

const pieces = 24;

// Grid lines on z = 0, split into short pieces whose vertex alpha fades out radially.
function gridLines(centre: Vector3, reach: number, step: number, keep: (i: number) => boolean, tint: Tint) {
  const c = toColor(tint);
  const points: number[] = [];
  const colors: number[] = [];
  const push = (x: number, y: number) => {
    points.push(x, y, 0);
    const fade = Math.max(0, 1 - Math.hypot(x - centre.x, y - centre.y) / reach);
    colors.push(c.r, c.g, c.b, fade * tint.alpha);
  };
  const line = (x0: number, y0: number, x1: number, y1: number) => {
    for (let k = 0; k < pieces; k++) {
      push(x0 + ((x1 - x0) * k) / pieces, y0 + ((y1 - y0) * k) / pieces);
      push(x0 + ((x1 - x0) * (k + 1)) / pieces, y0 + ((y1 - y0) * (k + 1)) / pieces);
    }
  };
  const indices = (mid: number) =>
    Array.from({ length: Math.floor((2 * reach) / step) + 1 }, (_, k) => Math.ceil((mid - reach) / step) + k);
  indices(centre.x)
    .filter(keep)
    .forEach((i) => line(i * step, centre.y - reach, i * step, centre.y + reach));
  indices(centre.y)
    .filter(keep)
    .forEach((j) => line(centre.x - reach, j * step, centre.x + reach, j * step));
  return new BufferGeometry()
    .setAttribute("position", new BufferAttribute(new Float32Array(points), 3))
    .setAttribute("color", new BufferAttribute(new Float32Array(colors), 4));
}

export function Grid({ box, palette }: { box: Box3; palette: Palette }) {
  const r = radius(box);
  const geometries = useMemo(() => {
    const centre = box.getCenter(new Vector3());
    const step = gridStep(box);
    return [
      gridLines(centre, r * 6, step, (i) => i % 10 !== 0, palette["grid-minor"]),
      gridLines(centre, r * 6, step, (i) => i % 10 === 0, palette["grid-major"]),
    ];
  }, [box, r, palette]);
  return (
    <group position={[0, 0, Math.min(0, box.min.z) - r * 1e-3]}>
      {geometries.map((g, i) => (
        <lineSegments key={i} geometry={g} renderOrder={-1}>
          <lineBasicMaterial vertexColors transparent depthWrite={false} />
        </lineSegments>
      ))}
      <Axis x={r} y={0} tint={palette["axis-x"]} />
      <Axis x={0} y={r} tint={palette["axis-y"]} />
    </group>
  );
}

// Origin lines stay under half opacity so the canvas still reads see-through where they cross a hole.
function Axis({ x, y, tint }: { x: number; y: number; tint: Tint }) {
  const g = useMemo(() => new BufferGeometry().setFromPoints([new Vector3(), new Vector3(x, y, 0)]), [x, y]);
  return (
    <lineSegments geometry={g}>
      <lineBasicMaterial color={toColor(tint)} transparent opacity={0.45} depthWrite={false} />
    </lineSegments>
  );
}
