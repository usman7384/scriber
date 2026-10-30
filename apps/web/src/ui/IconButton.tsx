import type { ComponentProps } from "react";
import { cx } from "./cx";
import { Icon, type IconName } from "./icons";
import { Tooltip } from "./Tooltip";
import "./ui.css";

interface Props extends Omit<ComponentProps<"button">, "children" | "aria-label"> {
  icon: IconName;
  label: string;
  variant?: "default" | "ghost";
}

export function IconButton({ icon, label, variant = "ghost", type = "button", className, ...rest }: Props) {
  return (
    <Tooltip text={label} describe={false}>
      <button
        type={type}
        aria-label={label}
        className={cx("ui-button ui-icon-button", className)}
        data-variant={variant}
        {...rest}
      >
        <Icon name={icon} />
      </button>
    </Tooltip>
  );
}
