import { expect, it } from "vitest";
import { resolveTheme } from "./theme";

it("resolves system from the OS and keeps an explicit choice", () => {
  expect(resolveTheme("system", true)).toBe("dark");
  expect(resolveTheme("system", false)).toBe("light");
  expect(resolveTheme("light", true)).toBe("light");
  expect(resolveTheme("dark", false)).toBe("dark");
});
