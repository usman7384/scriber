import { useT } from "../i18n";

export function Pending({ error }: { error?: string | undefined }) {
  const t = useT();
  return error ? (
    <p role="alert" className="pending">
      {error}
    </p>
  ) : (
    <p className="pending">{t.loading}</p>
  );
}
