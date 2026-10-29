import type { SyntheticEvent } from "react";

const stop = (e: SyntheticEvent) => e.stopPropagation();

// DOM overlays live inside the canvas container, where react-three-fiber would read their clicks as missed picks.
export const ownPointer = { onPointerDown: stop, onPointerUp: stop, onClick: stop };
