import type { ReactNode } from "react";
import { Icon, type IconName } from "./icons";

interface Props {
  icon?: IconName;
  tone?: "default" | "accent";
  remove?: { label: string; onClick: () => void };
  children: ReactNode;
}

export function Chip({ icon, tone = "default", remove, children }: Props) {
  return (
    <span className="ui-chip" data-tone={tone}>
      {icon && <Icon name={icon} size={14} />}
      <span className="ui-chip-text" title={typeof children === "string" ? children : undefined}>
        {children}
      </span>
      {remove && (
        <button type="button" className="ui-chip-remove" aria-label={remove.label} onClick={remove.onClick}>
          <Icon name="close" size={12} />
        </button>
      )}
    </span>
  );
}
