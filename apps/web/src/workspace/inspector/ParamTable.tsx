import type { Param } from "../../api";
import { useT } from "../../i18n";
import { Provenance } from "../../ui/Provenance";
import { fixed } from "../params/bounds";

// Read-only values (shared links, version previews); with `base`, a changed value shows what it was.
export function ParamTable({ params, base }: { params: Param[]; base?: Param[] | undefined }) {
  const t = useT();
  if (params.length === 0) return <p className="ws-muted">{t.params.none}</p>;
  const was = (p: Param) => base?.find((b) => b.name === p.name)?.value;
  return (
    <table className="ws-ptable" aria-label={t.shared.parameters}>
      <tbody>
        {params.map((p) => {
          const before = was(p);
          const changed = before !== undefined && before !== p.value;
          return (
            <tr key={p.name} data-changed={changed || undefined}>
              <th scope="row">{p.label}</th>
              <td className="mono">{fixed(p.value, p.unit)}</td>
              <td>
                <Provenance source={p.provenance.source} />
              </td>
              {base && (
                <td className="mono ws-muted">{changed ? t.params.was(fixed(before, p.unit)) : ""}</td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
