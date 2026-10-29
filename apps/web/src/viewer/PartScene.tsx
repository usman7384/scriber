import { Edges, useGLTF } from "@react-three/drei";
import { useEffect, useEffectEvent, useMemo, useState, type RefObject } from "react";
import { Vector3 } from "three";
import type { Finding, Vec3 } from "../api";
import { CameraRig } from "./CameraRig";
import { Dimensions } from "./Dimensions";
import { DrivingChip, type Driving } from "./DrivingChip";
import { FindingPins, type PinActions, type PinText } from "./FindingPins";
import { Grid } from "./Grid";
import { toColor, type Palette } from "./palette";
import { bounds, cadParts, radius, type Frame, type View } from "./scene";
import { TriadSync } from "./Triad";

export interface Hit {
  point: Vec3;
  normal: Vec3;
}

export interface SceneProps {
  url: string;
  view: { name: View };
  free: Frame | undefined;
  palette: Palette;
  edges: boolean;
  dims: boolean;
  axes: [string, string, string];
  hidden: string[];
  selected?: string | undefined;
  driving?: Driving | undefined;
  findings: Finding[];
  pinText: PinText;
  finding?: number | undefined;
  pinActions?: PinActions | undefined;
  triad: RefObject<SVGSVGElement | null>;
  onPick: (part: string, hit: Hit) => void;
  onLoad: (size: Vector3) => void;
}

export function PartScene(p: SceneProps) {
  const { scene } = useGLTF(p.url, false);
  const parts = useMemo(() => cadParts(scene), [scene]);
  const box = useMemo(() => bounds(parts), [parts]);
  const loaded = useEffectEvent(p.onLoad);
  useEffect(() => {
    loaded(box.getSize(new Vector3()));
  }, [box]);
  const [hover, setHover] = useState<string>();
  const [base, edge, accent] = [p.palette.part, p.palette["part-edge"], p.palette.accent].map(toColor);
  const tinted = base?.clone().lerp(accent ?? base, 0.14);
  return (
    <>
      <CameraRig view={p.view} box={box} free={p.free} />
      <Grid box={box} palette={p.palette} />
      {parts.map((part, i) => {
        if (p.hidden.includes(part.name)) return null;
        const marked = part.name === p.selected || part.name === hover;
        return (
          <mesh
            key={i}
            name={part.name}
            geometry={part.geometry}
            onPointerOver={(e) => {
              e.stopPropagation();
              setHover(part.name);
            }}
            onPointerOut={() => setHover(undefined)}
            onClick={(e) => {
              e.stopPropagation();
              const n = e.face?.normal ?? { x: 0, y: 0, z: 0 };
              p.onPick(part.name, { point: e.point.toArray(), normal: [n.x, n.y, n.z] });
            }}
          >
            <meshStandardMaterial
              color={part.name === p.selected ? tinted : base}
              roughness={0.85}
              metalness={0}
            />
            {(p.edges || marked) && <Edges threshold={15} color={marked ? accent : edge} />}
          </mesh>
        );
      })}
      {p.dims && <Dimensions box={box} axes={p.axes} tint={p.palette.faint} />}
      {p.driving && (
        <DrivingChip
          key={p.driving.at.join()}
          driving={p.driving}
          reach={radius(box) * 0.4}
          tint={p.palette.accent}
        />
      )}
      <FindingPins findings={p.findings} text={p.pinText} selected={p.finding} actions={p.pinActions} />
      <TriadSync svg={p.triad} />
    </>
  );
}
