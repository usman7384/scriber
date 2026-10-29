import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import type { GraphView as Graph } from "../api";
import { GraphView } from "./GraphView";

const graph: Graph = {
  nodes: [
    { id: "f1", type: "file", name: "spec.pdf" },
    { id: "r1", type: "requirement", name: "REQ-1" },
    { id: "r2", type: "requirement", name: "REQ-2" },
    { id: "m1", type: "model", name: "Sensor plate" },
  ],
  edges: [
    { src: "f1", dst: "r1", type: "states" },
    { src: "f1", dst: "r2", type: "states" },
    { src: "m1", dst: "r1", type: "satisfies" },
  ],
  counts: { entities: 4, relations: 3 },
};

it("draws one labelled node per entity, shows counters and toggles fullscreen", () => {
  const { container } = render(<GraphView graph={graph} />);
  expect(container.querySelectorAll("circle.node")).toHaveLength(4);
  expect(container.querySelectorAll("line.edge")).toHaveLength(3);
  expect([...container.querySelectorAll(".src-node text")].map((t) => t.textContent)).toEqual([
    "spec.pdf",
    "REQ-1",
    "REQ-2",
    "Sensor plate",
  ]);
  expect(screen.getByText("4 entities · 3 relations")).toBeInTheDocument();
  expect(screen.getAllByRole("listitem").map((li) => li.textContent?.trim())).toEqual([
    "file",
    "requirement",
    "model",
  ]);
  const panel = screen.getByRole("region", { name: "Knowledge graph" });
  fireEvent.click(screen.getByRole("button", { name: "Fullscreen" }));
  expect(panel).toHaveClass("fullscreen");
  fireEvent.keyDown(panel, { key: "Escape" });
  expect(panel).not.toHaveClass("fullscreen");
});
