import { exportUrl, type ExportFormat } from "../api";

const formats: [ExportFormat, string][] = [
  ["step", "STEP"],
  ["stl", "STL"],
  ["glb", "GLB"],
  ["py", "Script"],
];

export function ExportMenu({ modelId, version }: { modelId: string; version: number }) {
  return (
    <details className="menu">
      <summary className="button secondary">Export</summary>
      <ul>
        {formats.map(([fmt, label]) => (
          <li key={fmt}>
            <a href={exportUrl(modelId, fmt, version)} download>
              {label}
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}
