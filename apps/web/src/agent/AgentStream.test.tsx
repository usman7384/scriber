import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import { api, type Job, type Step } from "../api";
import { FakeEventSource, param, version } from "../test-utils";
import { AgentStatus } from "./AgentStatus";
import { AgentStream } from "./AgentStream";

beforeEach(() => {
  vi.restoreAllMocks();
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

const step = (
  kind: string,
  attempt: number,
  elapsed_ms: number,
  message: string,
  progress?: number,
): Step => ({
  kind,
  attempt,
  elapsed_ms,
  message,
  ...(progress !== undefined && { progress }),
});

const ended = (status: Job["status"], over: Partial<Job> = {}): Job => ({
  id: "j1",
  kind: "refine",
  status,
  project_id: "p1",
  model_id: "m1",
  version: 2,
  created: "2026-10-26T10:00:00Z",
  steps: [],
  ...over,
});

const stream = () => FakeEventSource.instances[0];

it("lists steps in arrival order, marks the failed check and links the repair to it", () => {
  vi.spyOn(api, "versions").mockResolvedValue([]);
  render(<AgentStream jobId="j1" variant="dock" />);
  expect(stream()?.url).toBe("/jobs/j1/events");
  act(() => {
    stream()?.emit("step", step("requirements", 0, 500, "REQ-1 plate 120 x 80 x 6", 10));
    stream()?.emit("step", step("emit", 1, 17281, "answer of 1984 chars", 40));
    stream()?.emit("step", step("check", 1, 17300, "holes overlap", 60));
    stream()?.emit("step", step("repair", 2, 34687, "answer of 1949 chars", 70));
  });
  const region = screen.getByRole("region", { name: "Generation timeline" });
  const items = within(region).getAllByRole("listitem");
  expect(items.map((li) => li.querySelector(".step-kind")?.textContent)).toEqual([
    "Requirements",
    "Model written",
    "Check",
    "Repair",
  ]);
  expect(items.map((li) => li.dataset.state)).toEqual(["pass", "pass", "fail", "pass"]);
  expect(items[3]).toHaveTextContent("Repairs the failed check above");
  expect(items[3]).toHaveTextContent("attempt 2");
  expect(items[3]).toHaveTextContent("34.7 s");
  expect(within(region).getByRole("progressbar", { name: "Progress" })).toHaveValue(70);
  expect(within(region).getByRole("status")).toHaveTextContent("running");
});

it("ends a card with the parameter diff, Open and Download STL", async () => {
  vi.spyOn(api, "versions").mockResolvedValue([
    version(1),
    version(2, { origin: "refine", params: [param({ value: 130 })] }),
  ]);
  const onDone = vi.fn();
  render(
    <MemoryRouter>
      <AgentStream jobId="j1" variant="card" onDone={onDone} />
    </MemoryRouter>,
  );
  act(() => stream()?.emit("step", step("done", 1, 9100, "1 parameter changed", 100)));
  act(() => stream()?.emit("done", ended("done")));
  expect(onDone).toHaveBeenCalledWith(ended("done"));
  expect(screen.getByRole("status")).toHaveTextContent("done");
  expect(screen.getByText("Done · v2")).toBeInTheDocument();
  expect(await screen.findByText("~ Plate Length 120.00 → 130.00 mm")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open model" })).toHaveAttribute("href", "/m/m1");
  expect(screen.getByRole("link", { name: "Download STL" })).toHaveAttribute(
    "href",
    "/models/m1/export?fmt=stl&version=2",
  );
});

it("collapses the dock when the job ends and offers Retry on failure", () => {
  const onRetry = vi.fn();
  render(<AgentStream jobId="j1" variant="dock" onRetry={onRetry} />);
  act(() => stream()?.emit("step", step("check", 1, 900, "wall too thin")));
  act(() => stream()?.emit("failed", ended("failed", { error: "no valid model after 3 attempts" })));
  expect(screen.getByRole("alert")).toHaveTextContent("no valid model after 3 attempts");
  expect(screen.getByRole("list", { hidden: true })).not.toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Expand" }));
  expect(screen.getByRole("list")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(onRetry).toHaveBeenCalledTimes(1);
});

it("says what the agent did last and reverts an agent version by restoring the one before", () => {
  const onRevert = vi.fn();
  const versions = [
    version(1),
    version(2, { origin: "refine", checks: [{ description: "size", passed: true, actual: 120 }] }),
  ];
  const { rerender } = render(<AgentStatus versions={versions} onRevert={onRevert} />);
  expect(screen.getByRole("status")).toHaveTextContent(/^v2 · refine · .+ · 1\/1 checks pass$/);
  fireEvent.click(screen.getByRole("button", { name: "Revert v2 by restoring v1 as a new version" }));
  expect(onRevert).toHaveBeenCalledWith(1);

  rerender(<AgentStatus versions={[...versions, version(3)]} onRevert={onRevert} />);
  expect(screen.queryByRole("button", { name: /Revert/ })).toBeNull();

  const running = ended("running", { steps: [step("check", 1, 900, "")] });
  rerender(<AgentStatus job={running} versions={versions} onRevert={onRevert} />);
  expect(screen.getByRole("status")).toHaveTextContent("Agent at work: Check");
  expect(screen.queryByRole("button", { name: /Revert/ })).toBeNull();
});
