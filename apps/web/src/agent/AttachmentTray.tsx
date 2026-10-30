import { useT } from "../i18n";
import { IconButton } from "../ui/IconButton";
import { Icon, type IconName } from "../ui/icons";
import type { Attachment, AttachKind } from "./useAttachments";
import "./agent.css";

const glyph: Record<AttachKind, IconName> = { image: "image", mesh: "mesh", spec: "document" };

interface Props {
  items: Attachment[];
  onRetry: (a: Attachment) => void;
  onRemove: (key: number) => void;
}

export function AttachmentTray({ items, onRetry, onRemove }: Props) {
  const t = useT();
  const a = t.agent.attach;
  if (items.length === 0) return null;
  const state = (x: Attachment) =>
    x.status === "uploading"
      ? a.uploading(x.progress)
      : x.status === "reading"
        ? a.reading(x.progress)
        : x.status === "ready"
          ? a.facts(x.facts ?? 0)
          : `${a.failed}: ${x.error ?? ""}`;
  return (
    <ul className="agent-tray" aria-label={t.prompt.attachments}>
      {items.map((x) => (
        <li key={x.key} className="agent-attachment" data-status={x.status}>
          <span title={a.kinds[x.kind]}>
            <Icon name={glyph[x.kind]} size={14} />
          </span>
          <span className="agent-attachment-name" title={x.file.name}>
            {x.file.name}
          </span>
          <span className="agent-attachment-state mono">
            {x.status === "failed" && <Icon name="fail" size={12} />}
            {x.status === "ready" && <Icon name="pass" size={12} />}
            {state(x)}
          </span>
          {(x.status === "uploading" || x.status === "reading") && (
            <progress
              className="agent-hairline"
              value={x.progress}
              max={100}
              aria-label={a.progress(x.file.name)}
            />
          )}
          {x.status === "failed" && (
            <button type="button" className="agent-link" onClick={() => onRetry(x)}>
              {a.retry}
            </button>
          )}
          <IconButton
            icon="close"
            label={`${t.prompt.remove} ${x.file.name}`}
            onClick={() => onRemove(x.key)}
          />
        </li>
      ))}
    </ul>
  );
}

export function AttachButton({ onFiles }: { onFiles: (files: File[]) => void }) {
  const t = useT();
  return (
    <label className="ui-button agent-attach" data-variant="ghost">
      <Icon name="attach" />
      {t.agent.attach.attach}
      <input
        type="file"
        multiple
        className="agent-sr"
        onChange={(e) => {
          onFiles([...(e.target.files ?? [])]);
          e.target.value = "";
        }}
      />
    </label>
  );
}
