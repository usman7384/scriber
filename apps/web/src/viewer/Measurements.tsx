import { Html } from "@react-three/drei";
import { useMemo } from "react";
import { BoxGeometry, EdgesGeometry, Vector3, type Box3 } from "three";
import { mm } from "../format";

export function Measurements({ box }: { box: Box3 }) {
  const size = box.getSize(new Vector3());
  const center = box.getCenter(new Vector3());
  const edges = useMemo(
    () => new EdgesGeometry(new BoxGeometry(size.x, size.y, size.z)),
    [size.x, size.y, size.z],
  );
  const { min, max } = box;
  const labels: [string, number, [number, number, number]][] = [
    ["L", size.x, [center.x, min.y, min.z]],
    ["W", size.y, [max.x, center.y, min.z]],
    ["H", size.z, [max.x, min.y, center.z]],
  ];
  return (
    <group>
      <lineSegments geometry={edges} position={center}>
        <lineBasicMaterial color="#f0883e" />
      </lineSegments>
      {labels.map(([axis, value, at]) => (
        <Html key={axis} position={at} center className="measure-label">
          {axis} {mm(value)}
        </Html>
      ))}
    </group>
  );
}
