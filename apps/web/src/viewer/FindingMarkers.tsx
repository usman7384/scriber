import { Html } from "@react-three/drei";
import type { Finding } from "../api";

export function FindingMarkers({
  findings,
  label,
}: {
  findings: Finding[];
  label: (message: string) => string;
}) {
  return findings.flatMap((f, i) =>
    f.location ? (
      <Html key={i} position={f.location.point} center>
        <span className={`marker ${f.severity}`} tabIndex={0} aria-label={label(f.message)}>
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
