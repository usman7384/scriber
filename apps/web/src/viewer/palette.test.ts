import { expect, it } from "vitest";
import { parseColor, toColor } from "./palette";

it("splits token colours into channels and an alpha", () => {
  expect(parseColor(" #9aa4ae")).toEqual({ rgb: [154, 164, 174], alpha: 1 });
  expect(parseColor("rgb(140 160 180 / 13%)")).toEqual({ rgb: [140, 160, 180], alpha: 0.13 });
  expect(parseColor("rgba(40, 60, 80, 0.5)")).toEqual({ rgb: [40, 60, 80], alpha: 0.5 });
  expect(() => parseColor("tomato")).toThrow(/unsupported/);
  expect(toColor(parseColor("#ff0000")).getHex()).toBe(0xff0000);
});
