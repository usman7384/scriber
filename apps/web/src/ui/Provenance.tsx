import { useT } from "../i18n";

const monograms: Record<string, string> = {
  prompt: "PRM",
  document: "DOC",
  rule: "RUL",
  standard: "STD",
  user_edit: "USR",
  mesh_fit: "FIT",
  vision: "VIS",
  default: "DEF",
};

export function Provenance({ source }: { source: string }) {
  const t = useT();
  return (
    <abbr
      className="ui-prov"
      data-assumed={source === "default" || undefined}
      title={t.source[source] ?? source}
    >
      {monograms[source] ?? source.slice(0, 3).toUpperCase()}
    </abbr>
  );
}
