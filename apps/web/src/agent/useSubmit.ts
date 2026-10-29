import { useState } from "react";
import type { Job } from "../api";

export type OnJob = (job: Job, resend: () => Promise<Job>) => void;

// build may wait (for attachments) before it returns the request; the same request is handed back for Retry.
export function useSubmit(onJob: OnJob) {
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string>();
  const submit = async (build: () => Promise<() => Promise<Job>>, sent: () => void) => {
    setSending(true);
    setError(undefined);
    try {
      const request = await build();
      onJob(await request(), request);
      sent();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSending(false);
    }
  };
  return { sending, error, submit };
}
