import type { ComponentProps } from "react";
import { cx } from "./cx";
import { Icon, type IconName } from "./icons";
import "./ui.css";

export interface ButtonProps extends ComponentProps<"button"> {
  variant?: "default" | "primary" | "ghost";
  icon?: IconName;
}

export function Button({
  variant = "default",
  icon,
  type = "button",
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button type={type} className={cx("ui-button", className)} data-variant={variant} {...rest}>
      {icon && <Icon name={icon} />}
      {children}
    </button>
  );
}
