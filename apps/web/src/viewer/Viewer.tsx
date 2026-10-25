import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useState } from "react";
import type { Finding } from "../api";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { mm } from "../format";
import { Model, type ModelInfo } from "./Model";
import type { View } from "./scene";

const views: [View, string][] = [
  ["top", "Top"],
  ["front", "Front"],
  ["right", "Right"],
  ["iso", "Iso"],
];

interface Props {
  url: string;
  findings: Finding[];
  selected?: string | undefined;
  onSelect: (part: string | undefined) => void;
  onLoad: (info: ModelInfo) => void;
}

export function Viewer({ url, findings, selected, onSelect, onLoad }: Props) {
  const [view, setView] = useState<{ name: View }>({ name: "iso" });
  const [edges, setEdges] = useState(true);
  const [measure, setMeasure] = useState(true);
  const [size, setSize] = useState<ModelInfo["size"]>();
  return (
    <div className="viewer">
      <div className="viewer-tools" role="toolbar" aria-label="View">
        {views.map(([name, label]) => (
          <button
            key={name}
            type="button"
            className="secondary small"
            aria-pressed={view.name === name}
            onClick={() => setView({ name })}
          >
            {label}
          </button>
        ))}
        <label className="toggle">
          <input type="checkbox" checked={edges} onChange={(e) => setEdges(e.target.checked)} />
          Edges
        </label>
        <label className="toggle">
          <input type="checkbox" checked={measure} onChange={(e) => setMeasure(e.target.checked)} />
          Measure
        </label>
        {size && (
          <span className="muted small push" aria-label="Bounding box">
            {mm(size.x)} × {mm(size.y)} × {mm(size.z)}
          </span>
        )}
      </div>
      <ErrorBoundary
        fallback={
          <p className="empty">The 3D view could not start (WebGL unavailable or model failed to load).</p>
        }
      >
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
              url={url}
              view={view}
              edges={edges}
              measure={measure}
              findings={findings}
              selected={selected}
              onSelect={onSelect}
              onLoad={(info) => {
                setSize(info.size);
                onLoad(info);
              }}
            />
          </Suspense>
          <OrbitControls makeDefault />
        </Canvas>
      </ErrorBoundary>
    </div>
  );
}
