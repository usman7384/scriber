import type { ReactNode } from "react";
import { useT } from "../i18n";
import { Icon } from "./icons";

export type StatusState = "pass" | "warn" | "fail";

const word: Record<StatusState, string> = { pass: "pass", warn: "warning", fail: "fail" };

export function Status({ state, children }: { state: StatusState; children?: ReactNode }) {
  const t = useT();
  return (
    <span className="ui-status" data-state={state}>
      <Icon name={state} size={14} />
      {children ?? t.status[word[state]]}
    </span>
  );
}
