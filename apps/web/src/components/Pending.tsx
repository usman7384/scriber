export function Pending({ error }: { error?: string | undefined }) {
  return error ? (
    <p role="alert" className="error">
      {error}
    </p>
  ) : (
    <p className="muted">Loading…</p>
  );
}
