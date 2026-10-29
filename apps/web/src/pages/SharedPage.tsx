import { useParams } from "react-router";
import { api, apiUrl, type ExportFormat } from "../api";
import { Pending } from "../components/Pending";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { Viewer } from "../viewer/Viewer";
import { ChecksPopover } from "../workspace/ChecksPopover";
import { DeliverMenu } from "../workspace/DeliverMenu";
import { Inspector } from "../workspace/inspector/Inspector";
import { Workspace } from "../workspace/Workspace";

const labels: [ExportFormat, string][] = [
  ["step", "STEP"],
  ["stl", "STL"],
  ["glb", "GLB"],
];

// The workspace, read-only: no command bar or rail, the inspector shows values, Deliver offers the shared files.
export function SharedPage() {
  const shareId = useParams().shareId ?? "";
  const shared = useResource(`shared:${shareId}`, () => api.shared(shareId));
  const t = useT();
  if (!shared.data) return <Pending error={shared.error} />;
  const { title, version } = shared.data;
  const names: [ExportFormat, string][] = [...labels, ["py", t.deliver.script], ["ir", t.deliver.ir]];
  const links = names.flatMap(([fmt, label]): [string, string][] => {
    const href = version.files[fmt];
    return href ? [[label, apiUrl(href)]] : [];
  });
  return (
    <Workspace
      title={title}
      version={version.number}
      badges={
        <>
          <ChecksPopover version={version} />
          <span className="ws-tag">{t.shared.badge}</span>
        </>
      }
      actions={<DeliverMenu heading={t.deliver.files} links={links} />}
      viewport={
        version.files.glb && (
          <Viewer url={apiUrl(version.files.glb)} findings={version.findings} onSelect={() => undefined} />
        )
      }
      inspector={<Inspector title={title} version={version} components={[]} />}
    />
  );
}
