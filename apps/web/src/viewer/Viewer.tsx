import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useState } from "react";
import type { Vector3 } from "three";
import type { Finding } from "../api";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { mm } from "../format";
import { useT } from "../i18n";
import { Model, type Hit } from "./Model";
import type { View } from "./scene";

const views: View[] = ["top", "front", "right", "iso"];

interface Props {
  url: string;
  findings: Finding[];
  selected?: string | undefined;
  onSelect: (part: string | undefined) => void;
  onPickFace?: (hit: Hit) => void;
}

export function Viewer({ url, findings, selected, onSelect, onPickFace }: Props) {
  const [view, setView] = useState<{ name: View }>({ name: "iso" });
  const [edges, setEdges] = useState(true);
  const [measure, setMeasure] = useState(true);
  const [faceMode, setFaceMode] = useState(false);
  const t = useT().viewer;
  const [size, setSize] = useState<Vector3>();
  return (
    <div className="viewer">
      <div className="viewer-tools" role="toolbar" aria-label={t.toolbar}>
        {views.map((name) => (
          <button
            key={name}
            type="button"
            className="secondary small"
            aria-pressed={view.name === name}
            onClick={() => setView({ name })}
          >
            {t.views[name]}
          </button>
        ))}
        <label className="toggle">
          <input type="checkbox" checked={edges} onChange={(e) => setEdges(e.target.checked)} />
          {t.edges}
        </label>
        {onPickFace && (
          <button
            type="button"
            className="secondary small"
            aria-pressed={faceMode}
            onClick={() => setFaceMode(!faceMode)}
          >
            {t.face}
          </button>
        )}
        <label className="toggle">
          <input type="checkbox" checked={measure} onChange={(e) => setMeasure(e.target.checked)} />
          {t.measure}
        </label>
        {size && (
          <span className="muted small push" aria-label={t.bbox}>
            {mm(size.x)} × {mm(size.y)} × {mm(size.z)}
          </span>
        )}
      </div>
      <ErrorBoundary fallback={<p className="empty">{t.noWebgl}</p>}>
        <Canvas
          frameloop="demand"
          camera={{ up: [0, 0, 1], fov: 35, near: 1, far: 100000, position: [200, -200, 160] }}
          gl={{ preserveDrawingBuffer: true }}
          onPointerMissed={() => onSelect(undefined)}
        >
          <ambientLight intensity={0.6} />
          <directionalLight position={[1, -2, 3]} intensity={1.6} />
          <directionalLight position={[-2, 1, -1]} intensity={0.5} />
          <Suspense fallback={null}>
            <Model
              axes={t.axes}
              finding={t.finding}
              url={url}
              view={view}
              edges={edges}
              measure={measure}
              findings={findings}
              selected={selected}
              onSelect={(part, hit) => (faceMode ? onPickFace?.(hit) : onSelect(part))}
              onLoad={setSize}
            />
          </Suspense>
          <OrbitControls makeDefault />
        </Canvas>
      </ErrorBoundary>
    </div>
  );
}
