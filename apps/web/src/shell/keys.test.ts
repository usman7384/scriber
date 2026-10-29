import { describe, expect, it } from "vitest";
import { isTyping, keyCaps, matches } from "./keys";

const key = (
  k: string,
  mods: Partial<Record<"ctrlKey" | "metaKey" | "altKey" | "shiftKey", boolean>> = {},
) => ({
  key: k,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  shiftKey: false,
  ...mods,
});

describe("matches", () => {
  it("treats Ctrl and Cmd as mod and compares the other modifiers", () => {
    expect(matches(key("k", { ctrlKey: true }), "mod+k")).toBe(true);
    expect(matches(key("K", { metaKey: true }), "mod+k")).toBe(true);
    expect(matches(key("k"), "mod+k")).toBe(false);
    expect(matches(key("E", { ctrlKey: true, shiftKey: true }), "mod+shift+e")).toBe(true);
    expect(matches(key("e", { ctrlKey: true }), "mod+shift+e")).toBe(false);
    expect(matches(key("1", { altKey: true }), "1")).toBe(false);
  });

  it("ignores Shift for punctuation, which needs it on some layouts", () => {
    expect(matches(key("?", { shiftKey: true }), "?")).toBe(true);
    expect(matches(key("[", {}), "[")).toBe(true);
  });
});

it("spells shortcuts for the platform", () => {
  expect(keyCaps("mod+k", false)).toEqual(["Ctrl", "K"]);
  expect(keyCaps("mod+shift+e", true)).toEqual(["⌘", "⇧", "E"]);
  expect(keyCaps("escape", false)).toEqual(["Esc"]);
  expect(keyCaps("mod+enter", false)).toEqual(["Ctrl", "⏎"]);
});

it("knows when the user is typing", () => {
  expect(isTyping(document.createElement("input"))).toBe(true);
  expect(isTyping(document.createElement("textarea"))).toBe(true);
  expect(isTyping(document.createElement("button"))).toBe(false);
  expect(isTyping(null)).toBe(false);
});
