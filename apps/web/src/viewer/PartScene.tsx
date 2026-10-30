import { Edges, useGLTF } from "@react-three/drei";
import { useEffect, useEffectEvent, useMemo, useState, type RefObject } from "react";
import { Box3, BufferAttribute, BufferGeometry, Vector3 } from "three";
import type { FaceMesh, Finding, Vec3 } from "../api";
import { CameraRig } from "./CameraRig";
import { Dimensions } from "./Dimensions";
import { DrivingChip, type Driving } from "./DrivingChip";
import { explodeOffsets } from "./explode";
import { FindingPins, type PinActions, type PinText } from "./FindingPins";
import { Grid } from "./Grid";
import { toColor, type Palette } from "./palette";
import { bounds, cadParts, radius, type Frame, type View } from "./scene";
import { TriadSync } from "./Triad";

export interface Hit {
  point: Vec3;
  normal: Vec3;
}

export interface AssemblyPart {
  id: string;
  name: string;
  parent?: string | null | undefined;
  axis?: Vec3 | null | undefined;
}

export interface Highlight {
  part: string;
  faces: FaceMesh[];
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
  assembly?: AssemblyPart[] | undefined;
  explode?: number | undefined;
  highlight?: Highlight | undefined;
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
  const exploding = p.explode !== undefined;
  const plan = useMemo(() => {
    const names = new Map((p.assembly ?? []).map((a) => [a.id, a.name]));
    const joints = new Map((p.assembly ?? []).map((a) => [a.name, a]));
    // a part can arrive as several meshes; it explodes as one, around their joint bounds
    const boxes = new Map<string, Box3>();
    for (const part of parts) {
      const b = part.geometry.boundingBox;
      if (b) boxes.set(part.name, (boxes.get(part.name) ?? new Box3()).union(b));
    }
    return [...boxes].map(([name, box]) => {
      const a = joints.get(name);
      return { name, parent: a?.parent ? names.get(a.parent) : undefined, axis: a?.axis, box };
    });
  }, [parts, p.assembly]);
  const offsets = useMemo(() => explodeOffsets(plan, p.explode ?? 0), [plan, p.explode]);
  // Exploding frames the parts fully apart once, so dragging the amount never moves the camera.
  const frame = useMemo(() => {
    if (!exploding) return box;
    const apart = explodeOffsets(plan, 1);
    return plan.reduce(
      (b, part) => b.union(part.box.clone().translate(apart.get(part.name) ?? new Vector3())),
      box.clone(),
    );
  }, [exploding, plan, box]);
  const idName = useMemo(() => new Map((p.assembly ?? []).map((a) => [a.id, a.name])), [p.assembly]);
  const offsetOf = (id?: string | null) => (id ? offsets.get(idName.get(id) ?? id) : undefined);
  const shift = (point: Vec3, id?: string | null): Vec3 => {
    const o = offsetOf(id);
    return o ? [point[0] + o.x, point[1] + o.y, point[2] + o.z] : point;
  };
  const pins = p.findings.map((f) =>
    f.location ? { ...f, location: { ...f.location, point: shift(f.location.point, f.part) } } : f,
  );
  const lit = useMemo(() => p.highlight && faceGeometry(p.highlight.faces), [p.highlight]);
  return (
    <>
      <CameraRig view={p.view} box={frame} free={p.free} />
      <Grid box={box} palette={p.palette} />
      {parts.map((part, i) => {
        if (p.hidden.includes(part.name)) return null;
        const marked = part.name === p.selected || part.name === hover;
        return (
          <mesh
            key={i}
            name={part.name}
            geometry={part.geometry}
            position={offsets.get(part.name)}
            onPointerOver={(e) => {
              e.stopPropagation();
              setHover(part.name);
            }}
            onPointerOut={() => setHover(undefined)}
            onClick={(e) => {
              e.stopPropagation();
              const n = e.face?.normal ?? { x: 0, y: 0, z: 0 };
              // picks report assembled coordinates, whatever the explode amount
              const at = e.point.clone().sub(offsets.get(part.name) ?? new Vector3());
              p.onPick(part.name, { point: at.toArray(), normal: [n.x, n.y, n.z] });
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
      {lit && p.highlight && (
        <mesh geometry={lit} position={offsetOf(p.highlight.part)} renderOrder={1}>
          <meshBasicMaterial
            color={accent}
            transparent
            opacity={0.5}
            depthWrite={false}
            polygonOffset
            polygonOffsetFactor={-2}
            polygonOffsetUnits={-2}
          />
        </mesh>
      )}
      {p.dims && !exploding && <Dimensions box={box} axes={p.axes} tint={p.palette.faint} />}
      {p.driving && (
        <DrivingChip
          key={p.driving.at.join()}
          driving={{ ...p.driving, at: shift(p.driving.at, p.driving.part) }}
          reach={radius(box) * 0.4}
          tint={p.palette.accent}
        />
      )}
      <FindingPins findings={pins} text={p.pinText} selected={p.finding} actions={p.pinActions} />
      <TriadSync svg={p.triad} />
    </>
  );
}

function faceGeometry(faces: FaceMesh[]): BufferGeometry {
  const positions = faces.flatMap((f) => f.positions);
  let base = 0;
  const indices = faces.flatMap((f) => {
    const shifted = f.indices.map((i) => i + base);
    base += f.positions.length / 3;
    return shifted;
  });
  const g = new BufferGeometry();
  g.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
  g.setIndex(indices);
  return g;
}
