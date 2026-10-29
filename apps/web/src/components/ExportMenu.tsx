import { api, exportUrl, type ExportFormat } from "../api";
import { useT } from "../i18n";

interface Props {
  modelId: string;
  version: number;
  freecad: boolean;
  onError: (e: Error) => void;
}

export function ExportMenu({ modelId, version, freecad, onError }: Props) {
  const t = useT().exportMenu;
  const formats: [ExportFormat, string][] = [
    ["step", "STEP"],
    ["stl", "STL"],
    ["glb", "GLB"],
    ["py", t.script],
  ];
  // a plain download link cannot show why the API refused, so the FreeCAD file is fetched first
  const downloadFcstd = () =>
    api.exportFile(modelId, "fcstd", version).then(({ blob, name }) => {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = name;
      link.click();
      URL.revokeObjectURL(link.href);
    }, onError);
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
        {freecad && (
          <li>
            <button type="button" className="link" onClick={() => void downloadFcstd()}>
              {t.freecad}
            </button>
          </li>
        )}
      </ul>
    </details>
  );
}
