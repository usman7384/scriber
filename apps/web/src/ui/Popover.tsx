import { useId, useRef, useState, type ReactNode, type RefObject, type ToggleEvent } from "react";
import { anchorTo, type Align } from "./place";
import "./ui.css";

export interface PopoverTrigger {
  ref: RefObject<HTMLButtonElement | null>;
  popoverTarget: string;
  "aria-haspopup": "dialog";
  "aria-expanded": boolean;
  "aria-controls": string;
}

interface Props {
  label: string;
  trigger: (props: PopoverTrigger) => ReactNode;
  align?: Align;
  children: ReactNode;
}

// Native popover: light dismiss, Esc and focus return come from the browser.
export function Popover({ label, trigger, align = "start", children }: Props) {
  const id = useId();
  const anchor = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const toggle = (e: ToggleEvent<HTMLDivElement>) => {
    const isOpen = e.newState === "open";
    setOpen(isOpen);
    if (isOpen && anchor.current) anchorTo(e.currentTarget, anchor.current, "bottom", align);
    // Hidden until placed: the toggle event fires after the browser has shown it at its default spot.
    e.currentTarget.toggleAttribute("data-placed", isOpen);
  };
  return (
    <>
      {trigger({
        ref: anchor,
        popoverTarget: id,
        "aria-haspopup": "dialog",
        "aria-expanded": open,
        "aria-controls": id,
      })}
      <div id={id} popover="auto" role="dialog" aria-label={label} className="ui-popover" onToggle={toggle}>
        {children}
      </div>
    </>
  );
}
