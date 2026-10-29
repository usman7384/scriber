import { describe, expect, it } from "vitest";
import { messages } from "./i18n";
import * as agent from "./i18n/agent";
import * as common from "./i18n/common";
import * as home from "./i18n/home";
import * as shell from "./i18n/shell";
import * as workspace from "./i18n/workspace";

const namespaces = [common, shell, workspace, agent, home];

describe("message namespaces", () => {
  it("own disjoint keys, so no namespace shadows another when aggregated", () => {
    const keys = namespaces.flatMap((ns) => Object.keys(ns.en));
    expect(new Set(keys).size).toBe(keys.length);
    expect(Object.keys(messages.en)).toEqual(keys);
  });

  it("give German the same keys in the same order as English", () => {
    const shape = (node: unknown): unknown =>
      typeof node === "object" && node !== null
        ? Object.entries(node).map(([k, v]) => [k, shape(v)])
        : typeof node;
    expect(shape(messages.de)).toEqual(shape(messages.en));
  });
});
