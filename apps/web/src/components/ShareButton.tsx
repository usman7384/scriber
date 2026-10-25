import { useState } from "react";
import { api, apiUrl } from "../api";

export function ShareButton({ modelId, version }: { modelId: string; version: number }) {
  const [url, setUrl] = useState<string>();
  const [error, setError] = useState<string>();
  const share = () =>
    api.share(modelId, version).then(
      (s) => setUrl(new URL(apiUrl(s.url), location.href).href),
      (e: Error) => setError(e.message),
    );
  return (
    <span className="row">
      <button type="button" className="secondary" onClick={share}>
        Share
      </button>
      {url && (
        <>
          <input readOnly value={url} aria-label="Share link" onFocus={(e) => e.target.select()} />
          <button type="button" className="secondary" onClick={() => navigator.clipboard.writeText(url)}>
            Copy
          </button>
        </>
      )}
      {error && (
        <span role="alert" className="error">
          {error}
        </span>
      )}
    </span>
  );
}
