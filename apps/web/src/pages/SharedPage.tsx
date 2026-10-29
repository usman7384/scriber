import { useParams } from "react-router";
import { api, apiUrl } from "../api";
import { Pending } from "../components/Pending";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { Viewer } from "../viewer/Viewer";

export function SharedPage() {
  const shareId = useParams().shareId ?? "";
  const shared = useResource(`shared:${shareId}`, () => api.shared(shareId));
  const t = useT().shared;
  if (!shared.data) return <Pending error={shared.error} />;
  const { title, version } = shared.data;
  return (
    <section className="stack">
      <header className="row">
        <h1>{title}</h1>
        <span className="badge plain">v{version.number}</span>
        <span className="badge">{t.badge}</span>
      </header>
      {version.files.glb && (
        <Viewer url={apiUrl(version.files.glb)} findings={version.findings} onSelect={() => undefined} />
      )}
      <table aria-label={t.parameters}>
        <tbody>
          {version.params.map((p) => (
            <tr key={p.name}>
              <th scope="row">{p.label}</th>
              <td>
                {p.value} {p.unit}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
