import { exportUrl, type ExportFormat } from "../api";
import { useT } from "../i18n";

export function ExportMenu({ modelId, version }: { modelId: string; version: number }) {
  const t = useT().exportMenu;
  const formats: [ExportFormat, string][] = [
    ["step", "STEP"],
    ["stl", "STL"],
    ["glb", "GLB"],
    ["py", t.script],
  ];
  return (
    <details className="menu">
      <summary className="button secondary">{t.export}</summary>
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
