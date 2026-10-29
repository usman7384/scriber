import { expect, it, vi } from "vitest";
import { createRegistry, type Action } from "./actions";

const action = (id: string, label = id): Action => ({
  id,
  group: "view",
  label: () => label,
  run: () => undefined,
});

it("adds and removes actions per registration, the latest registration of an id winning", () => {
  const registry = createRegistry();
  const listener = vi.fn();
  registry.subscribe(listener);
  const first = [action("a", "first"), action("b")];
  const removeFirst = registry.add(first);
  const removeSecond = registry.add([action("a", "second")]);
  expect(registry.list().map((a) => [a.id, a.label({} as never)])).toEqual([
    ["a", "second"],
    ["b", "b"],
  ]);
  removeSecond();
  expect(registry.list().map((a) => a.label({} as never))).toEqual(["first", "b"]);
  registry.add(first)();
  removeFirst();
  expect(registry.list()).toEqual([]);
  expect(listener).toHaveBeenCalledTimes(6);
});
