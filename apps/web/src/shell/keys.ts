import { useEffect, useEffectEvent } from "react";
import { enabled, type ActionContext, type ActionRegistry } from "./actions";

export interface KeyLike {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
}

interface Shortcut {
  mod: boolean;
  alt: boolean;
  shift: boolean;
  key: string;
}

export const PALETTE_KEY = "mod+k";

const parse = (shortcut: string): Shortcut => {
  const parts = shortcut.toLowerCase().split("+");
  const key = parts.pop() ?? "";
  return { mod: parts.includes("mod"), alt: parts.includes("alt"), shift: parts.includes("shift"), key };
};

// Punctuation needs Shift on some layouts ("?" on US, "/" on German), so Shift is not compared for it.
export const matches = (e: KeyLike, shortcut: string) => {
  const s = parse(shortcut);
  const punctuation = s.key.length === 1 && !/[a-z0-9]/.test(s.key);
  return (
    e.key.toLowerCase() === s.key &&
    (e.ctrlKey || e.metaKey) === s.mod &&
    e.altKey === s.alt &&
    (punctuation || e.shiftKey === s.shift)
  );
};

const named: Record<string, string> = { enter: "⏎", escape: "Esc", arrowleft: "←", arrowright: "→" };

export const keyCaps = (shortcut: string, mac: boolean) => {
  const s = parse(shortcut);
  return [
    ...(s.mod ? [mac ? "⌘" : "Ctrl"] : []),
    ...(s.alt ? [mac ? "⌥" : "Alt"] : []),
    ...(s.shift ? [mac ? "⇧" : "Shift"] : []),
    named[s.key] ?? (s.key.length === 1 ? s.key.toUpperCase() : s.key[0]?.toUpperCase() + s.key.slice(1)),
  ];
};

export const isMac = () => /Mac|iPhone|iPad/.test(navigator.userAgent);

export const isTyping = (target: EventTarget | null) =>
  target instanceof HTMLElement &&
  (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));

// One window listener: Ctrl+K everywhere, registered single-key shortcuts outside fields and dialogs.
export function useShortcutLayer(
  registry: ActionRegistry,
  context: () => ActionContext,
  togglePalette: () => void,
) {
  const onKey = useEffectEvent((e: KeyboardEvent) => {
    if (matches(e, PALETTE_KEY)) {
      e.preventDefault();
      togglePalette();
      return;
    }
    const inDialog = e.target instanceof Element && e.target.closest("dialog");
    if (e.defaultPrevented || inDialog || isTyping(e.target)) return;
    const ctx = context();
    const action = registry
      .list()
      .find((a) => a.shortcut !== undefined && matches(e, a.shortcut) && enabled(a, ctx));
    if (!action) return;
    e.preventDefault();
    action.run("");
  });
  useEffect(() => {
    const listener = (e: KeyboardEvent) => onKey(e);
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);
}
