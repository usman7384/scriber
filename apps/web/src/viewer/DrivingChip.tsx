import { Html } from "@react-three/drei";
import { useMemo, useState, type KeyboardEvent } from "react";
import { BufferGeometry, Vector3 } from "three";
import type { Vec3 } from "../api";
import { toColor, type Tint } from "./palette";
import { ownPointer } from "./stop";

export interface Driving {
  at: Vec3;
  part?: string | undefined;
  normal: Vec3;
  value: number;
  unit: string;
  label: string;
  busy: boolean;
  onCommit: (value: number) => void;
}

const stepOf = (e: { shiftKey: boolean; altKey: boolean }) => (e.shiftKey ? 10 : e.altKey ? 0.1 : 1);

// The parameter behind the picked face, typed in place on the model: Enter applies, Esc cancels, arrows step.
export function DrivingChip({ driving, reach, tint }: { driving: Driving; reach: number; tint: Tint }) {
  const { at, normal, value, unit, label, busy, onCommit } = driving;
  const [draft, setDraft] = useState(value.toFixed(2));
  const end = useMemo(
    () => new Vector3(...normal).multiplyScalar(reach).add(new Vector3(...at)),
    [at, normal, reach],
  );
  const leader = useMemo(() => new BufferGeometry().setFromPoints([new Vector3(...at), end]), [at, end]);
  const key = (e: KeyboardEvent<HTMLInputElement>) => {
    const n = Number(draft);
    if (e.key === "Enter" && Number.isFinite(n) && n !== value) onCommit(n);
    if (e.key === "Escape") {
      setDraft(value.toFixed(2));
      e.currentTarget.blur();
    }
    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      e.preventDefault();
      const next = (Number.isFinite(n) ? n : value) + (e.key === "ArrowUp" ? 1 : -1) * stepOf(e);
      setDraft(next.toFixed(2));
    }
  };
  return (
    <group>
      <lineSegments geometry={leader}>
        <lineBasicMaterial color={toColor(tint)} />
      </lineSegments>
      <Html position={end} center className="ws-dim ws-dim-driving" zIndexRange={[200, 101]}>
        <input
          {...ownPointer}
          className="ws-dim-input"
          aria-label={label}
          inputMode="decimal"
          value={draft}
          disabled={busy}
          size={Math.max(draft.length, 4)}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={key}
          onFocus={(e) => e.target.select()}
        />
        <span className="ws-dim-unit">{unit}</span>
      </Html>
    </group>
  );
}
