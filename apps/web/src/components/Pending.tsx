import { useT } from "../i18n";

export function Pending({ error }: { error?: string | undefined }) {
  const t = useT();
  return error ? (
    <p role="alert" className="error">
      {error}
    </p>
  ) : (
    <p className="muted">{t.loading}</p>
  );
}
