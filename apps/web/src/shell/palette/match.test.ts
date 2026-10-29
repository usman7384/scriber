import { describe, expect, it } from "vitest";
import type { Messages } from "../../i18n";
import type { Action } from "../actions";
import { outOfBounds, parseAssignment, rank, remember, score } from "./match";

const action = (over: Partial<Action> & Pick<Action, "id">): Action => ({
  group: "navigate",
  label: () => over.id,
  run: () => undefined,
  ...over,
});
const thickness = { name: "plate_thickness", label: "Thickness", value: 6, unit: "mm", min: 3, max: 20 };
const ctx = { pathname: "/m/m1", query: "" };
const labelOf = (a: Action) => a.label({} as Messages);

describe("score", () => {
  it("prefers an early substring over a scattered subsequence and rejects a miss", () => {
    const sub = score("lib", "Library");
    const scattered = score("lby", "Library");
    expect(sub).toBeGreaterThan(scattered ?? Infinity);
    expect(score("xyz", "Library")).toBeUndefined();
    expect(score("", "Library")).toBe(0);
  });
});

describe("parseAssignment", () => {
  it("reads name = value with an optional unit and a comma decimal", () => {
    expect(parseAssignment("thick = 7")).toEqual({ name: "thick", value: 7 });
    expect(parseAssignment(" edge offset=12,5 mm ")).toEqual({ name: "edge offset", value: 12.5 });
    expect(parseAssignment("thick = seven")).toBeUndefined();
    expect(parseAssignment("= 7")).toBeUndefined();
  });

  it("checks bounds", () => {
    expect(outOfBounds(thickness, 7)).toBe(false);
    expect(outOfBounds(thickness, 2)).toBe(true);
    expect(outOfBounds({ ...thickness, max: null }, 99)).toBe(false);
  });
});

describe("rank", () => {
  const actions = [
    action({ id: "go.library", label: () => "Library" }),
    action({ id: "help.open", group: "help", label: () => "Help" }),
    action({ id: "param.t", group: "parameters", label: () => "Thickness", param: thickness }),
    action({ id: "agent.ask", group: "agent", label: () => "As a change to the plate" }),
    action({ id: "hidden", label: () => "Hidden", when: ({ pathname }) => pathname === "/" }),
  ];

  it("lists recent actions first and every group in palette order when the query is empty", () => {
    const sections = rank(actions, "", ctx, labelOf, ["help.open", "gone"]);
    expect(sections.map((s) => s.group)).toEqual(["recent", "parameters", "navigate"]);
    expect(sections[0]?.rows.map((r) => r.action.id)).toEqual(["help.open"]);
  });

  it("filters by label, leaves out actions whose when() is false, and always offers the agent", () => {
    const sections = rank(actions, "lib", ctx, labelOf, []);
    expect(sections.map((s) => [s.group, s.rows.map((r) => r.action.id)])).toEqual([
      ["agent", ["agent.ask"]],
      ["navigate", ["go.library"]],
    ]);
  });

  it("turns name = value into a parameter row carrying the value", () => {
    const [params] = rank(actions, "thick = 7", ctx, labelOf, []);
    expect(params?.group).toBe("parameters");
    expect(params?.rows).toEqual([expect.objectContaining({ value: 7, label: "Thickness" })]);
  });
});

it("remembers recent ids newest first, without duplicates", () => {
  expect(remember(["a", "b", "c"], "b", 3)).toEqual(["b", "a", "c"]);
  expect(remember(["a", "b", "c"], "d", 3)).toEqual(["d", "a", "b"]);
});
