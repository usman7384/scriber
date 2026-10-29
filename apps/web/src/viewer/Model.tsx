import { Edges, useGLTF } from "@react-three/drei";
import { useEffect, useEffectEvent, useMemo } from "react";
import { Vector3 } from "three";
import type { Finding, Vec3 } from "../api";
import { CameraRig } from "./CameraRig";
import { FindingMarkers } from "./FindingMarkers";
import { Measurements } from "./Measurements";
import { bounds, cadParts, type View } from "./scene";

export interface Hit {
  point: Vec3;
  normal: Vec3;
}

interface Props {
  url: string;
  view: { name: View };
  edges: boolean;
  measure: boolean;
  findings: Finding[];
  selected?: string | undefined;
  onSelect: (part: string, hit: Hit) => void;
  onLoad: (size: Vector3) => void;
}

export function Model({ url, view, edges, measure, findings, selected, onSelect, onLoad }: Props) {
  const { scene } = useGLTF(url, false);
  const parts = useMemo(() => cadParts(scene), [scene]);
  const box = useMemo(() => bounds(parts), [parts]);
  const loaded = useEffectEvent(onLoad);
  useEffect(() => {
    loaded(box.getSize(new Vector3()));
  }, [box]);
  return (
    <>
      <CameraRig view={view} box={box} />
      {parts.map((p, i) => (
        <mesh
          key={i}
          name={p.name}
          geometry={p.geometry}
          onClick={(e) => {
            e.stopPropagation();
            const n = e.face?.normal ?? { x: 0, y: 0, z: 0 };
            onSelect(p.name, { point: e.point.toArray(), normal: [n.x, n.y, n.z] });
          }}
        >
          <meshStandardMaterial
            color={p.name === selected ? "#3b82f6" : "#b9c2cc"}
            roughness={0.55}
            metalness={0.15}
          />
          {edges && <Edges threshold={15} color="#1d2733" />}
        </mesh>
      ))}
      {measure && <Measurements box={box} />}
      <FindingMarkers findings={findings} />
    </>
  );
}
