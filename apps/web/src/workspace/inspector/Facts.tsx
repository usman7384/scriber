import type { Version } from "../../api";
import { useT } from "../../i18n";

export function Facts({
  metrics,
  material,
}: {
  metrics: Version["metrics"];
  material?: string | null | undefined;
}) {
  const t = useT();
  if (!metrics) return null;
  const e = t.editor;
  const facts: [string, string][] = [
    [e.mass, metrics.mass_g != null ? `${metrics.mass_g.toFixed(1)} g` : t.inspector.unset],
    [e.volume, `${(metrics.volume / 1000).toFixed(2)} cm³`],
    [e.material, material ?? t.inspector.unset],
    [e.size, `${metrics.bbox.map((v) => v.toFixed(2)).join(" × ")} mm`],
  ];
  return (
    <dl className="ws-facts">
      {facts.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd className="mono">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
