import { Html } from "@react-three/drei";
import type { Finding } from "../api";

export function FindingMarkers({ findings }: { findings: Finding[] }) {
  return findings.flatMap((f, i) =>
    f.location ? (
      <Html key={i} position={f.location.point} center>
        <span className={`marker ${f.severity}`} tabIndex={0} aria-label={`Finding: ${f.message}`}>
          !
          <span role="tooltip">
            {f.message}
            {f.suggestion && <em> {f.suggestion}</em>}
          </span>
        </span>
      </Html>
    ) : (
      []
    ),
  );
}
