import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { api, type ContextFile, type Job } from "../api";
import { FakeEventSource } from "../test-utils";
import { PromptPanel } from "./PromptPanel";

beforeEach(() => {
  vi.restoreAllMocks();
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

const job = (id: string, kind: Job["kind"]): Job => ({
  id,
  kind,
  status: "queued",
  project_id: "p1",
  created: "2026-10-26T10:00:00Z",
  steps: [],
});

it("fills the prompt box from an example chip", () => {
  render(<PromptPanel projectId="p1" onJob={vi.fn()} />);
  const chip = screen.getAllByRole("button").find((b) => b.className === "chip");
  fireEvent.click(chip as HTMLElement);
  expect(screen.getByLabelText("Describe the part")).toHaveValue(chip?.textContent);
});

it("uploads attachments to the project context first and references them in the generate call", async () => {
  const names = ["sketch.png", "old-part.stl", "spec.md"];
  const stored = names.map((name, i) => ({ id: `f${i}`, name, uploaded: "2026-10-26T10:00:00Z" }));
  vi.spyOn(api, "upload").mockResolvedValue(names.map((_, i) => job(`ingest${i}`, "ingest")));
  vi.spyOn(api, "context").mockResolvedValue({ files: stored as ContextFile[], stats: {} as never });
  const generate = vi.spyOn(api, "generate").mockResolvedValue(job("g1", "generate"));
  const onJob = vi.fn();
  render(<PromptPanel projectId="p1" onJob={onJob} />);

  fireEvent.change(screen.getByLabelText("Describe the part"), {
    target: { value: "Bracket like the sketch" },
  });
  ["+ Image", "+ Mesh", "+ Spec file"].forEach((label, i) =>
    fireEvent.change(screen.getByLabelText(label), { target: { files: [new File(["x"], names[i] ?? "")] } }),
  );
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "fdm" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate" }));

  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(3));
  act(() =>
    FakeEventSource.instances.forEach((s, i) =>
      s.emit("done", { ...job(`ingest${i}`, "ingest"), status: "done" }),
    ),
  );
  await waitFor(() => expect(onJob).toHaveBeenCalled());
  expect(api.upload).toHaveBeenCalledWith("p1", expect.arrayContaining([expect.any(File)]));
  expect(generate).toHaveBeenCalledWith("p1", {
    prompt: "Bracket like the sketch",
    process: "fdm",
    attachments: ["f0", "f1", "f2"],
  });
});
