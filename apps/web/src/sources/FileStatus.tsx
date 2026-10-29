import { useT } from "../i18n";
import { Icon } from "../ui/icons";

const glyph = { processed: "pass", failed: "fail", processing: "clock", uploading: "clock" } as const;

export function FileStatus({
  status,
  error,
}: {
  status: keyof typeof glyph;
  error?: string | null | undefined;
}) {
  const t = useT();
  return (
    <span className="src-status" data-state={status} title={error ?? undefined}>
      <Icon name={glyph[status]} size={14} />
      {t.status[status]}
    </span>
  );
}
