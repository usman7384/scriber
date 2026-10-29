import { createContext, useContext, useEffect, useSyncExternalStore } from "react";
import type { Param } from "../api";
import type { Messages } from "../i18n";
import type { IconName } from "../ui/icons";

// Palette order (docs/design/UI_DIRECTION.md §3, Command palette).
export const groups = [
  "suggested",
  "parameters",
  "agent",
  "navigate",
  "view",
  "deliver",
  "settings",
  "help",
] as const;

export type ActionGroup = (typeof groups)[number];

export interface ActionContext {
  pathname: string;
  query: string;
}

export interface Action {
  id: string;
  group: ActionGroup;
  label: (t: Messages) => string;
  hint?: string;
  icon?: IconName;
  // "mod+k", "shift+e", "?", "[": mod is Ctrl, or Cmd on a Mac.
  shortcut?: string;
  when?: (ctx: ActionContext) => boolean;
  // A parameter the palette can set from "name = value".
  param?: Pick<Param, "name" | "label" | "value" | "unit" | "min" | "max">;
  // Gets the palette query: the agent's request for "agent" actions, the value as text for a param.
  run: (query: string) => void;
}

export interface ActionRegistry {
  add: (actions: readonly Action[]) => () => void;
  list: () => readonly Action[];
  subscribe: (listener: () => void) => () => void;
}

export const enabled = (action: Action, ctx: ActionContext) => action.when?.(ctx) ?? true;

export function createRegistry(): ActionRegistry {
  let sources: { actions: readonly Action[] }[] = [];
  let snapshot: readonly Action[] = [];
  const listeners = new Set<() => void>();
  const publish = () => {
    // The latest registration of an id wins.
    snapshot = [...new Map(sources.flatMap((s) => s.actions.map((a) => [a.id, a] as const))).values()];
    listeners.forEach((listener) => listener());
  };
  return {
    add: (actions) => {
      const source = { actions };
      sources = [...sources, source];
      publish();
      return () => {
        sources = sources.filter((s) => s !== source);
        publish();
      };
    },
    list: () => snapshot,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

export const ActionsContext = createContext<ActionRegistry | null>(null);

const useRegistry = () => {
  const registry = useContext(ActionsContext);
  if (!registry) throw new Error("useRegisterActions needs the shell's ActionsContext");
  return registry;
};

// Registers while mounted. Pass a memoised array: a new array re-registers on every render.
export function useRegisterActions(actions: readonly Action[]) {
  const registry = useRegistry();
  useEffect(() => registry.add(actions), [registry, actions]);
}

export function useActions() {
  const registry = useRegistry();
  return useSyncExternalStore(registry.subscribe, registry.list);
}
