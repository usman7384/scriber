import { useContext, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { SlotsContext, type SlotName } from "./context";

// Renders into the shell's chrome: "side" is the Home sidebar, "top" the workspace top bar.
export function ShellSlot({ name, children }: { name: SlotName; children: ReactNode }) {
  const target = useContext(SlotsContext)[name];
  return target ? createPortal(children, target) : null;
}
