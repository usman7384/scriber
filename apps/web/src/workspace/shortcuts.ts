import { useEffect, useEffectEvent } from "react";

const typing = (target: EventTarget | null) =>
  target instanceof HTMLElement &&
  (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));

// Single-key shortcuts for the workspace; ignored while typing or with Ctrl, Alt or Meta held.
export function useShortcuts(keys: Record<string, (() => void) | undefined>) {
  const run = useEffectEvent((e: KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented || typing(e.target)) return;
    const action = keys[e.key.length === 1 ? e.key.toLowerCase() : e.key];
    if (!action) return;
    e.preventDefault();
    action();
  });
  useEffect(() => {
    const listener = (e: KeyboardEvent) => run(e);
    addEventListener("keydown", listener);
    return () => removeEventListener("keydown", listener);
  }, []);
}
