export interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}
export type Side = "top" | "bottom";
export type Align = "start" | "center" | "end";

const gap = 6;
const edge = 8;

// Prefers `side`, flips when it does not fit, and keeps the box inside the viewport.
export function place(anchor: Box, size: Box, side: Side, align: Align, view: Box) {
  const above = anchor.top - gap - size.height;
  const below = anchor.top + anchor.height + gap;
  const fitsAbove = above >= edge;
  const fitsBelow = below + size.height <= view.height - edge;
  const top =
    side === "top" ? (fitsAbove || !fitsBelow ? above : below) : fitsBelow || !fitsAbove ? below : above;
  const x =
    align === "start"
      ? anchor.left
      : align === "end"
        ? anchor.left + anchor.width - size.width
        : anchor.left + (anchor.width - size.width) / 2;
  return {
    top: Math.max(edge, top),
    left: Math.max(edge, Math.min(x, view.width - edge - size.width)),
  };
}

export function anchorTo(el: HTMLElement, anchor: Element, side: Side, align: Align) {
  const view = { top: 0, left: 0, width: innerWidth, height: innerHeight };
  const { top, left } = place(anchor.getBoundingClientRect(), el.getBoundingClientRect(), side, align, view);
  el.style.top = `${top}px`;
  el.style.left = `${left}px`;
}
