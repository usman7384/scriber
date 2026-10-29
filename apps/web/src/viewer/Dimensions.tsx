import { Html } from "@react-three/drei";
import { useMemo } from "react";
import { BufferGeometry, type Box3 } from "three";
import { mm } from "../format";
import { toColor, type Tint } from "./palette";
import { boxDimensions } from "./scene";

// drei Html renders into its own React root, so the axis names come in as props.
export function Dimensions({ box, axes, tint }: { box: Box3; axes: [string, string, string]; tint: Tint }) {
  const dims = useMemo(() => boxDimensions(box), [box]);
  const lines = useMemo(() => new BufferGeometry().setFromPoints(dims.flatMap((d) => d.segments)), [dims]);
  return (
    <group>
      <lineSegments geometry={lines}>
        {/* Reference lines stay translucent: muted on screen, and never read as solid part in the canvas. */}
        <lineBasicMaterial color={toColor(tint)} transparent opacity={0.45} depthWrite={false} />
      </lineSegments>
      {dims.map((d) => (
        <Html
          key={d.axis}
          position={d.at}
          center
          className="measure-label ws-dim ws-dim-ref"
          zIndexRange={[100, 0]}
        >
          {axes[d.axis]} {mm(d.value)}
        </Html>
      ))}
    </group>
  );
}
