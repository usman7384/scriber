import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { ContextFile } from "../api";
import { FileTable } from "./FileTable";

const file = (id: string, name: string, kind: string): ContextFile => ({
  id,
  project_id: "p1",
  name,
  kind,
  role: "spec",
  status: "processed",
  facts: 3,
  rules: 0,
  uploaded: "2026-10-26T09:00:00Z",
  used_in: ["m1"],
});

const files = [
  file("f1", "motor-mount-spec.pdf", "pdf"),
  file("f2", "design-rules.md", "md"),
  file("f3", "nema17-motor.step", "step"),
];

const names = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((r) => r.querySelector("td")?.textContent);

it("shows every column and filters by the search text", () => {
  render(<FileTable files={files} onOpen={vi.fn()} onDelete={vi.fn()} />);
  expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
    "Name",
    "Type",
    "Status",
    "Facts",
    "Used in",
    "Uploaded",
    "Actions",
  ]);
  expect(names()).toHaveLength(3);
  fireEvent.change(screen.getByLabelText("Search files"), { target: { value: "MOTOR" } });
  expect(names()).toEqual(["motor-mount-spec.pdf", "nema17-motor.step"]);
  fireEvent.change(screen.getByLabelText("Search files"), { target: { value: "gearbox" } });
  expect(screen.getByText("No files match the search.")).toBeInTheDocument();
});

it("deletes a file only after confirmation", () => {
  const onDelete = vi.fn();
  render(<FileTable files={files} onOpen={vi.fn()} onDelete={onDelete} />);
  fireEvent.click(screen.getByRole("button", { name: "Delete design-rules.md" }));
  expect(onDelete).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
  expect(onDelete).toHaveBeenCalledExactlyOnceWith("f2");
});
