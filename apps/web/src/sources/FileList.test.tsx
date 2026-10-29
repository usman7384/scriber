import { fireEvent, render as renderDom, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { beforeAll, expect, it, vi } from "vitest";
import type { ContextFile } from "../api";
import { FileList } from "./FileList";

beforeAll(() => {
  HTMLElement.prototype.togglePopover = function (force?: boolean) {
    return this.toggleAttribute("data-open", force);
  };
});

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
  { ...file("f3", "nema17-motor.step", "step"), status: "failed" as const, error: "unreadable STEP" },
];

const render = (ui: ReactElement) => renderDom(<MemoryRouter>{ui}</MemoryRouter>);

const names = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((r) => r.querySelector("td")?.textContent);

it("keeps every column for assistive tech and filters by the search text", () => {
  render(<FileList files={files} onOpen={vi.fn()} onDelete={vi.fn()} />);
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

it("shows parse status as a glyph and a word, with the failure reason", () => {
  render(<FileList files={files} onOpen={vi.fn()} onDelete={vi.fn()} />);
  const failed = screen.getByText("failed").closest("span");
  expect(failed).toHaveAttribute("title", "unreadable STEP");
  expect(failed?.querySelector("[data-icon=fail]")).toBeInTheDocument();
  expect(screen.getAllByText("processed")).toHaveLength(2);
  expect(screen.getAllByText("3 facts")).toHaveLength(3);
});

it("teaches what sources are for when there are none", () => {
  render(<FileList files={[]} onOpen={vi.fn()} onDelete={vi.fn()} />);
  expect(screen.getByText(/become constraints the agent must meet/)).toBeInTheDocument();
});

it("deletes a file only after confirmation", () => {
  const onDelete = vi.fn();
  render(<FileList files={files} onOpen={vi.fn()} onDelete={onDelete} />);
  fireEvent.click(screen.getByRole("button", { name: "Delete design-rules.md" }));
  expect(onDelete).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
  expect(onDelete).toHaveBeenCalledExactlyOnceWith("f2");
});

it("chooses files as context and links the models each was used in", () => {
  const onChoose = vi.fn();
  render(
    <FileList
      files={files}
      chosen={["f1"]}
      titles={{ m1: "Sensor plate" }}
      onOpen={vi.fn()}
      onChoose={onChoose}
      onDelete={vi.fn()}
    />,
  );
  expect(screen.getAllByRole("link", { name: "Sensor plate" })).toHaveLength(3);
  fireEvent.click(screen.getByLabelText("Use design-rules.md as context"));
  expect(onChoose).toHaveBeenCalledExactlyOnceWith(["f1", "f2"]);
});
