import { useState } from "react";
import { api, type Printability } from "../api";

export interface PrintState {
  report?: Printability;
  error?: string;
  running: boolean;
  check: () => void;
}

export function usePrintCheck(modelId: string, version: number): PrintState {
  const [state, setState] = useState<{
    version: number;
    report?: Printability;
    error?: string;
    running: boolean;
  }>({ version, running: false });
  const current = state.version === version ? state : { version, running: false };
  const check = () => {
    setState({ version, running: true });
    api.slice(modelId, version).then(
      (report) => setState({ version, report, running: false }),
      (e: Error) => setState({ version, error: e.message, running: false }),
    );
  };
  return { ...current, check };
}
