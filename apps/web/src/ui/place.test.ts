import { describe, expect, it } from "vitest";
import { place } from "./place";

const view = { top: 0, left: 0, width: 1000, height: 800 };
const size = { top: 0, left: 0, width: 200, height: 100 };
const box = (left: number, top: number) => ({ left, top, width: 40, height: 20 });

describe("place", () => {
  it("puts a popover below its anchor, start-aligned", () => {
    expect(place(box(100, 100), size, "bottom", "start", view)).toEqual({ top: 126, left: 100 });
  });

  it("centres a tooltip above its anchor", () => {
    expect(place(box(400, 300), size, "top", "center", view)).toEqual({ top: 194, left: 320 });
  });

  it("flips to the other side when the preferred one does not fit", () => {
    expect(place(box(100, 750), size, "bottom", "start", view).top).toBe(644);
    expect(place(box(100, 20), size, "top", "center", view).top).toBe(46);
  });

  it("keeps the box inside the viewport horizontally", () => {
    expect(place(box(950, 100), size, "bottom", "start", view).left).toBe(792);
    expect(place(box(0, 100), size, "bottom", "end", view).left).toBe(8);
  });
});
