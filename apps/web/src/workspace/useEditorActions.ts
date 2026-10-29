import { useCallback, useEffect, useMemo, useRef } from "react";
import type { Param } from "../api";
import { useRegisterActions, type Action } from "../shell/actions";

interface Handlers {
  setParam: (name: string, value: number) => void;
  focusParam: (name: string) => void;
  refine: (instruction: string) => void;
  show: (n: number) => void;
  newGeneration: () => void;
}

interface Options extends Handlers {
  params: Param[];
  numbers: number[];
  shown: number;
  target?: string | undefined;
  editable: boolean;
}

// The workspace's palette entries: each parameter, the agent, the version steps, a new generation.
export function useEditorActions({ params, numbers, shown, target, editable, ...handlers }: Options) {
  const latest = useRef(handlers);
  useEffect(() => {
    latest.current = handlers;
  });
  const call = useCallback((go: (h: Handlers) => void) => go(latest.current), []);
  const at = numbers.indexOf(shown);
  const prev = numbers[at - 1];
  const next = numbers[at + 1];
  const actions = useMemo<Action[]>(() => {
    const step = (id: string, shortcut: string, to: number | undefined): Action => ({
      id: `versions.${id}`,
      group: "view",
      icon: "clock",
      shortcut,
      label: (t) => (id === "prev" ? t.editor.previousVersion : t.editor.nextVersion),
      when: () => to !== undefined,
      run: () => to !== undefined && call((h) => h.show(to)),
    });
    const always: Action[] = [
      step("prev", "[", prev),
      step("next", "]", next),
      {
        id: "agent.new",
        group: "navigate",
        icon: "plus",
        label: (t) => t.editor.newGeneration,
        run: () => call((h) => h.newGeneration()),
      },
    ];
    if (!editable) return always;
    return [
      ...always,
      {
        id: "agent.refine",
        group: "agent",
        label: (t) => t.editor.asChange(target ?? t.refine.whole),
        run: (query) => query.trim() && call((h) => h.refine(query.trim())),
      },
      ...params.map((p): Action => ({
        id: `param.${p.name}`,
        group: "parameters",
        hint: `${p.value} ${p.unit}`,
        label: () => p.label,
        param: p,
        run: (value) => {
          const n = Number(value.replace(",", "."));
          if (value.trim() === "" || !Number.isFinite(n)) return call((h) => h.focusParam(p.name));
          call((h) => h.setParam(p.name, n));
        },
      })),
    ];
  }, [call, params, prev, next, target, editable]);
  useRegisterActions(actions);
}
