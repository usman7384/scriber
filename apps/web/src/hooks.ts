import { useEffect, useEffectEvent, useState } from "react";
import { streamJob, type Job, type Step } from "./api";

const message = (e: unknown) => (e instanceof Error ? e.message : String(e));

export function useResource<T>(key: string, load: () => Promise<T>) {
  const [state, setState] = useState<{ key: string; data?: T; error?: string }>({ key: "" });
  const [nonce, setNonce] = useState(0);
  const run = useEffectEvent(load);
  useEffect(() => {
    let live = true;
    run().then(
      (data) => live && setState({ key, data }),
      (e: unknown) => live && setState({ key, error: message(e) }),
    );
    return () => {
      live = false;
    };
  }, [key, nonce]);
  const current = state.key === key;
  return {
    data: current ? state.data : undefined,
    error: current ? state.error : undefined,
    loading: !current,
    reload: () => setNonce((n) => n + 1),
  };
}

export interface JobState {
  steps: Step[];
  job?: Job;
  error?: string;
}

export function useJob(jobId: string | undefined, onEnd?: (job: Job) => void): JobState {
  const [state, setState] = useState<JobState & { id?: string }>({ steps: [] });
  const ended = useEffectEvent((job: Job) => onEnd?.(job));
  useEffect(() => {
    if (!jobId) return;
    const update = (patch: (s: JobState) => JobState) =>
      setState((s) => ({ ...patch(s.id === jobId ? s : { steps: [] }), id: jobId }));
    return streamJob(jobId, {
      onStep: (step) => update((s) => ({ ...s, steps: [...s.steps, step] })),
      onEnd: (job) => {
        update((s) => ({ ...s, job }));
        ended(job);
      },
      onError: (error) => update((s) => ({ ...s, error })),
    });
  }, [jobId]);
  return state.id === jobId ? state : { steps: [] };
}
