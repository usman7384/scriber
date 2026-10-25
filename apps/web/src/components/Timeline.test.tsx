import { act, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { FakeEventSource } from "../test-utils";
import { JobTimeline } from "./Timeline";

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

const step = (kind: string, attempt: number, elapsed_ms: number, message: string) => ({
  kind,
  attempt,
  elapsed_ms,
  message,
});

it("renders SSE steps in arrival order and ends on done", () => {
  const onEnd = vi.fn();
  render(<JobTimeline jobId="j1" onEnd={onEnd} />);
  const source = FakeEventSource.instances[0];
  expect(source?.url).toBe("/jobs/j1/events");
  expect(screen.getByRole("status")).toHaveTextContent("running");

  act(() => {
    source?.emit("step", step("requirements", 0, 500, "REQ-1 plate 120 x 80 x 6"));
    source?.emit("step", step("emit", 1, 17281, "answer of 1984 chars"));
    source?.emit("step", step("check", 1, 17300, "holes overlap"));
    source?.emit("step", step("repair", 2, 34687, "answer of 1949 chars"));
  });
  const items = within(screen.getByRole("list")).getAllByRole("listitem");
  expect(items.map((li) => li.querySelector(".step-kind")?.textContent)).toEqual([
    "requirements",
    "emit",
    "check",
    "repair",
  ]);
  expect(items[3]).toHaveTextContent("attempt 2");
  expect(items[3]).toHaveTextContent("34.7 s");

  const job = { id: "j1", status: "done", steps: [] };
  act(() => source?.emit("done", job));
  expect(screen.getByRole("status")).toHaveTextContent("done");
  expect(onEnd).toHaveBeenCalledWith(job);
  expect(source?.readyState).toBe(FakeEventSource.CLOSED);
});

it("shows the job error on failed", () => {
  render(<JobTimeline jobId="j2" />);
  act(() =>
    FakeEventSource.instances[0]?.emit("failed", { id: "j2", status: "failed", error: "interrupted" }),
  );
  expect(screen.getByRole("status")).toHaveTextContent("failed");
  expect(screen.getByRole("alert")).toHaveTextContent("interrupted");
});
