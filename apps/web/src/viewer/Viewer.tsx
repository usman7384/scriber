import { OrbitControls, OrthographicCamera, PerspectiveCamera } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useEffect, useRef, useState } from "react";
import type { Vector3 } from "three";
import type { Finding } from "../api";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { mm } from "../format";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { useShortcuts } from "../workspace/shortcuts";
import type { Driving } from "./DrivingChip";
import type { PinActions } from "./FindingPins";
import { usePalette } from "./palette";
import { PartScene, type Hit } from "./PartScene";
import { isOrtho, type Frame, type View } from "./scene";
import { TriadSvg } from "./Triad";
import "./viewer.css";

const views: [View, string][] = [
  ["top", "1"],
  ["front", "2"],
  ["right", "3"],
  ["iso", "0"],
];

interface Props {
  url: string;
  findings: Finding[];
  selected?: string | undefined;
  hidden?: string[];
  finding?: number | undefined;
  driving?: Driving | undefined;
  pinActions?: PinActions | undefined;
  onSelect: (part: string | undefined) => void;
  onPickFace?: ((hit: Hit) => void) | undefined;
}

// The free frame is a CSS box inset by the --frame-* variables; its rect tells the camera where to centre the part.
function useFreeFrame() {
  const root = useRef<HTMLDivElement>(null);
  const free = useRef<HTMLDivElement>(null);
  const [frame, setFrame] = useState<Frame>();
  useEffect(() => {
    const [r, f] = [root.current, free.current];
    if (!r || !f) return;
    const measure = () => {
      const [outer, inner] = [r.getBoundingClientRect(), f.getBoundingClientRect()];
      setFrame({
        left: inner.left - outer.left,
        top: inner.top - outer.top,
        width: inner.width,
        height: inner.height,
      });
    };
    const observer = new ResizeObserver(measure);
    observer.observe(f);
    observer.observe(r);
    return () => observer.disconnect();
  }, []);
  return { root, free, frame };
}

export function Viewer({
  url,
  findings,
  selected,
  hidden = [],
  finding,
  driving,
  pinActions,
  onSelect,
  onPickFace,
}: Props) {
  const [view, setView] = useState<{ name: View }>({ name: "iso" });
  const [edges, setEdges] = useState(true);
  const [dims, setDims] = useState(true);
  const [faceMode, setFaceMode] = useState(false);
  const [size, setSize] = useState<Vector3>();
  const { root, free, frame } = useFreeFrame();
  const triad = useRef<SVGSVGElement>(null);
  const palette = usePalette();
  const t = useT();
  const v = t.viewer;
  const pickFace = onPickFace && (() => setFaceMode((on) => !on));
  useShortcuts({
    ...Object.fromEntries(views.map(([name, key]) => [key, () => setView({ name })])),
    e: () => setEdges((on) => !on),
    m: () => setDims((on) => !on),
    p: pickFace,
  });
  const pinText = {
    name: (f: Finding) => v.finding(f.message, t.status[f.severity] ?? f.severity),
    detail: (f: Finding) =>
      f.measured != null && f.required != null
        ? t.findings.measured(f.measured.toFixed(2), f.required.toFixed(2))
        : undefined,
    rule: (f: Finding) => t.findings.rule(f.rule_id, f.binding),
    ask: t.findings.ask,
    showRule: t.findings.showRule,
  };
  const ortho = isOrtho(view.name);
  return (
    <div className="viewer ws-viewer" ref={root} data-picking={faceMode || undefined}>
      <div className="ws-free" ref={free}>
        <div className="ws-hud" role="toolbar" aria-label={v.toolbar}>
          {views.map(([name, key]) => (
            <Button
              key={name}
              variant="ghost"
              aria-pressed={view.name === name}
              aria-keyshortcuts={key}
              onClick={() => setView({ name })}
            >
              {v.views[name]}
            </Button>
          ))}
          <span className="ws-hud-rule" />
          <IconButton
            icon="edges"
            label={v.edges}
            aria-pressed={edges}
            aria-keyshortcuts="E"
            onClick={() => setEdges(!edges)}
          />
          <IconButton
            icon="dimension"
            label={v.measure}
            aria-pressed={dims}
            aria-keyshortcuts="M"
            onClick={() => setDims(!dims)}
          />
          {pickFace && (
            <IconButton
              icon="face"
              label={v.face}
              aria-pressed={faceMode}
              aria-keyshortcuts="P"
              onClick={pickFace}
            />
          )}
          {size && (
            <span className="ws-hud-bbox mono" aria-label={v.bbox}>
              {mm(size.x)} × {mm(size.y)} × {mm(size.z)}
            </span>
          )}
        </div>
      </div>
      <div className="ws-canvas">
        <ErrorBoundary fallback={<p className="ws-empty">{v.noWebgl}</p>}>
          <Canvas
            frameloop="demand"
            gl={{ preserveDrawingBuffer: true }}
            onPointerMissed={() => onSelect(undefined)}
          >
            <PerspectiveCamera makeDefault={!ortho} up={[0, 0, 1]} fov={35} near={1} far={100000} />
            <OrthographicCamera makeDefault={ortho} up={[0, 0, 1]} near={0.1} far={100000} />
            <ambientLight intensity={0.9} />
            <directionalLight position={[1, -2, 3]} intensity={1.3} />
            <directionalLight position={[-2, 1, -1]} intensity={0.5} />
            <Suspense fallback={null}>
              <PartScene
                url={url}
                view={view}
                free={frame}
                palette={palette}
                edges={edges}
                dims={dims}
                axes={v.axes}
                hidden={hidden}
                selected={selected}
                driving={driving}
                findings={findings}
                pinText={pinText}
                finding={finding}
                pinActions={pinActions}
                triad={triad}
                onPick={(part, hit) => (faceMode ? onPickFace?.(hit) : onSelect(part))}
                onLoad={setSize}
              />
            </Suspense>
            <OrbitControls makeDefault />
          </Canvas>
        </ErrorBoundary>
      </div>
      <TriadSvg ref={triad} />
    </div>
  );
}
