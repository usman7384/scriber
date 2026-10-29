import { useCallback, useEffect, useMemo, useRef } from "react";
import { useRegisterActions, type Action } from "./actions";
import { useShell, type BugTarget } from "./context";

export const BUG_ACTION = "help.bug";

// The workspace calls this with its canvas screenshot; Help and the palette then offer Report a bug.
export function useBugAction(target: BugTarget) {
  const { reportBug } = useShell();
  const latest = useRef(target);
  useEffect(() => {
    latest.current = target;
  });
  const open = useCallback(() => reportBug(latest.current), [reportBug]);
  const actions = useMemo<Action[]>(
    () => [{ id: BUG_ACTION, group: "help", icon: "warn", label: (t) => t.bug.open, run: open }],
    [open],
  );
  useRegisterActions(actions);
  return open;
}
