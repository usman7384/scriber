import { cloneElement, useId, useRef, type ReactElement, type SyntheticEvent } from "react";
import { anchorTo, type Side } from "./place";

interface Props {
  text: string;
  side?: Side;
  // false when the trigger already has the same text as its name (icon buttons).
  describe?: boolean;
  children: ReactElement<{ "aria-describedby"?: string }>;
}

// A hint popover sits in the top layer (never clipped by overflow or backdrop-filter) and leaves open menus alone.
export function Tooltip({ text, side = "top", describe = true, children }: Props) {
  const id = useId();
  const tip = useRef<HTMLSpanElement>(null);
  const show = (e: SyntheticEvent<HTMLSpanElement>) => {
    const anchor = e.currentTarget.firstElementChild;
    if (!tip.current || !anchor) return;
    tip.current.togglePopover(true);
    anchorTo(tip.current, anchor, side, "center");
  };
  const hide = () => tip.current?.togglePopover(false);
  return (
    <span
      className="ui-tip-anchor"
      onPointerEnter={show}
      onPointerLeave={hide}
      // Keyboard focus only: a sheet focusing its close button on open should not pop a tooltip.
      onFocus={(e) => e.target.matches(":focus-visible") && show(e)}
      onBlur={hide}
      onKeyDown={(e) => e.key === "Escape" && hide()}
    >
      {describe ? cloneElement(children, { "aria-describedby": id }) : children}
      <span ref={tip} id={id} role="tooltip" popover="hint" className="ui-tooltip" aria-hidden={!describe}>
        {text}
      </span>
    </span>
  );
}
