import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { api, type ContextFile, type Job } from "../api";
import { FakeEventSource } from "../test-utils";
import { CommandBar } from "./CommandBar";

const job = (id: string, kind: Job["kind"], status: Job["status"] = "queued"): Job => ({
  id,
  kind,
  status,
  project_id: "p1",
  created: "2026-10-26T10:00:00Z",
  steps: [],
});

const stored = (id: string, name: string, over: Partial<ContextFile> = {}) =>
  ({ id, name, uploaded: "2026-10-26T10:00:00Z", status: "processed", facts: 3, ...over }) as ContextFile;

beforeEach(() => {
  vi.restoreAllMocks();
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

const attach = (files: File[]) => fireEvent.change(screen.getByLabelText("Attach"), { target: { files } });

const finishIngest = (i: number) =>
  act(() => FakeEventSource.instances[i]?.emit("done", job(`ingest${i}`, "ingest", "done")));

it("fills the composer from a starter card", () => {
  render(<CommandBar mode="generate" projectId="p1" contextIds={[]} onJob={vi.fn()} />);
  const card = within(screen.getByRole("group", { name: "Example prompts" })).getAllByRole("button")[2];
  fireEvent.click(card as HTMLElement);
  expect(screen.getByLabelText("Describe the part")).toHaveValue(card?.textContent);
});

it("shows parse status per file and sends one generate with every ready id once they settle", async () => {
  const upload = vi.spyOn(api, "uploadWithProgress").mockImplementation(async (_, file, progress) => {
    progress(40);
    return [job(`ingest-${file.name}`, "ingest")];
  });
  vi.spyOn(api, "context").mockResolvedValue({
    files: [stored("f1", "sketch.png"), stored("f2", "old.stl"), stored("c1", "rules.md")],
    stats: {} as never,
  });
  const generate = vi.spyOn(api, "generate").mockResolvedValue(job("g1", "generate"));
  const onJob = vi.fn();
  render(<CommandBar mode="generate" projectId="p1" contextIds={["c1"]} onJob={onJob} />);

  attach([new File(["x"], "sketch.png", { type: "image/png" }), new File(["x"], "old.stl")]);
  const tray = screen.getByRole("list", { name: "Attachments" });
  await waitFor(() => expect(within(tray).getAllByText("reading 0 %")).toHaveLength(2));
  act(() => FakeEventSource.instances[0]?.emit("step", { kind: "ingest", progress: 50 }));
  expect(within(tray).getByText("reading 50 %")).toBeInTheDocument();
  expect(await screen.findByText("rules.md")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Describe the part"), {
    target: { value: "Bracket like the sketch" },
  });
  fireEvent.keyDown(screen.getByLabelText("Describe the part"), { key: "Enter", ctrlKey: true });
  expect(await screen.findByRole("button", { name: /Waiting for attachments/ })).toBeDisabled();
  expect(generate).not.toHaveBeenCalled();

  finishIngest(0);
  finishIngest(1);
  await waitFor(() => expect(onJob).toHaveBeenCalledTimes(1));
  expect(upload).toHaveBeenCalledTimes(2);
  expect(generate).toHaveBeenCalledWith("p1", {
    prompt: "Bracket like the sketch",
    process: "any",
    attachments: ["f1", "f2"],
    context_ids: ["c1"],
  });
  expect(screen.getByLabelText("Describe the part")).toHaveValue("");
  expect(screen.queryByRole("list", { name: "Attachments" })).toBeNull();

  const resend = onJob.mock.calls[0]?.[1] as () => Promise<Job>;
  await resend();
  expect(generate).toHaveBeenCalledTimes(2);
});

it("names a failed file's reason, retries it, and never blocks the others", async () => {
  const upload = vi
    .spyOn(api, "uploadWithProgress")
    .mockRejectedValueOnce(new Error("413 file too large"))
    .mockResolvedValue([job("ingest0", "ingest")]);
  vi.spyOn(api, "context").mockResolvedValue({ files: [stored("f1", "spec.pdf")], stats: {} as never });
  const generate = vi.spyOn(api, "generate").mockResolvedValue(job("g1", "generate"));
  render(<CommandBar mode="generate" projectId="p1" contextIds={[]} onJob={vi.fn()} />);

  attach([new File(["x"], "spec.pdf")]);
  expect(await screen.findByText("failed: 413 file too large")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
  finishIngest(0);
  expect(await screen.findByText("3 facts")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Remove spec.pdf" }));
  expect(screen.queryByText("3 facts")).toBeNull();

  upload.mockRejectedValueOnce(new Error("415 unsupported"));
  attach([new File(["x"], "notes.bin")]);
  expect(await screen.findByText("failed: 415 unsupported")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Describe the part"), { target: { value: "Plate 10 mm" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate" }));
  await waitFor(() => expect(generate).toHaveBeenCalledTimes(1));
  expect(generate.mock.calls[0]?.[1]).toMatchObject({ attachments: [] });
});

it("refines on Enter with the target and clears the target on Backspace in an empty bar", async () => {
  const refine = vi.spyOn(api, "refine").mockResolvedValue(job("r1", "refine"));
  const onClearTarget = vi.fn();
  const onJob = vi.fn();
  const { rerender } = render(
    <CommandBar
      mode="refine"
      modelId="m1"
      target={{ id: "plate", label: "Sensor mounting plate", kind: "part" }}
      onClearTarget={onClearTarget}
      onJob={onJob}
    />,
  );
  const chip = () => screen.getByRole("form", { name: "Refine" }).querySelector(".chip");
  expect(chip()).toHaveTextContent("Target: Sensor mounting plate");
  const box = screen.getByLabelText("Change request");
  expect(box).toHaveAttribute("placeholder", "What should change on Sensor mounting plate?");
  fireEvent.keyDown(box, { key: "Backspace" });
  expect(onClearTarget).toHaveBeenCalledTimes(1);

  fireEvent.change(box, { target: { value: "make it 10 mm thicker" } });
  fireEvent.keyDown(box, { key: "Enter" });
  await waitFor(() => expect(onJob).toHaveBeenCalledTimes(1));
  expect(refine).toHaveBeenCalledWith("m1", { instruction: "make it 10 mm thicker", target: "plate" });

  rerender(<CommandBar mode="refine" modelId="m1" onClearTarget={onClearTarget} onJob={onJob} busy />);
  expect(chip()).toHaveTextContent("Target: Entire object");
  fireEvent.change(box, { target: { value: "thinner" } });
  expect(screen.getByRole("button", { name: "Refine" })).toBeDisabled();
  expect(box.getAttribute("placeholder")).toMatch(/^Sending resumes/);
});

it("keeps the text and shows the error when a request fails", async () => {
  vi.spyOn(api, "refine").mockRejectedValue(new Error("model m1 not found"));
  render(<CommandBar mode="refine" modelId="m1" onClearTarget={vi.fn()} onJob={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Change request"), { target: { value: "rounder" } });
  fireEvent.click(screen.getByRole("button", { name: "Refine" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("model m1 not found");
  expect(screen.getByLabelText("Change request")).toHaveValue("rounder");
});

it("hands a leading slash to the palette instead of the agent", () => {
  const onCommand = vi.fn();
  const refine = vi.spyOn(api, "refine");
  render(
    <CommandBar mode="refine" modelId="m1" onClearTarget={vi.fn()} onJob={vi.fn()} onCommand={onCommand} />,
  );
  const box = screen.getByLabelText("Change request");
  fireEvent.change(box, { target: { value: "/export step" } });
  expect(screen.getByText(/Commands run from the palette/)).toBeInTheDocument();
  fireEvent.keyDown(box, { key: "Enter" });
  expect(onCommand).toHaveBeenCalledWith("export step");
  expect(refine).not.toHaveBeenCalled();
});

it("marks recognised quantities in the text", () => {
  const { container } = render(
    <CommandBar mode="refine" modelId="m1" onClearTarget={vi.fn()} onJob={vi.fn()} />,
  );
  fireEvent.change(screen.getByLabelText("Change request"), {
    target: { value: "use M3 screws, 6 mm deep" },
  });
  expect([...container.querySelectorAll("mark")].map((m) => m.textContent)).toEqual(["M3", "6 mm"]);
});
