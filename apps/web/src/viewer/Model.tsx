import { Edges, useGLTF } from "@react-three/drei";
import { useEffect, useEffectEvent, useMemo } from "react";
import { Vector3 } from "three";
import type { Finding } from "../api";
import { CameraRig } from "./CameraRig";
import { FindingMarkers } from "./FindingMarkers";
import { Measurements } from "./Measurements";
import { bounds, cadParts, type View } from "./scene";

export interface ModelInfo {
  parts: string[];
  size: Vector3;
}

interface Props {
  url: string;
  view: { name: View };
  edges: boolean;
  measure: boolean;
  findings: Finding[];
  selected?: string | undefined;
  onSelect: (part: string) => void;
  onLoad: (info: ModelInfo) => void;
}

export function Model({ url, view, edges, measure, findings, selected, onSelect, onLoad }: Props) {
  const { scene } = useGLTF(url, false);
  const parts = useMemo(() => cadParts(scene), [scene]);
  const box = useMemo(() => bounds(parts), [parts]);
  const loaded = useEffectEvent(onLoad);
  useEffect(() => {
    loaded({ parts: [...new Set(parts.map((p) => p.name))], size: box.getSize(new Vector3()) });
  }, [parts, box]);
  return (
    <>
      <CameraRig view={view} box={box} />
      {parts.map((p, i) => (
        <mesh
          key={i}
          geometry={p.geometry}
          onClick={(e) => {
            e.stopPropagation();
            onSelect(p.name);
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
