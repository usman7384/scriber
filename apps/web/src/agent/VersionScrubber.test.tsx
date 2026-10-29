import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { api, type Job, type Suggestion } from "../api";
import { param, version } from "../test-utils";
import { Proposals } from "./Proposals";
import { VersionScrubber } from "./VersionScrubber";

beforeEach(() => vi.restoreAllMocks());

const versions = [
  version(1, { thumbnail_url: "/models/m1/versions/1/thumbnail" }),
  version(2, { params: [param({ value: 130 })] }),
  version(3, { origin: "refine", prompt: "make it 10 mm thicker", params: [param({ value: 130 })] }),
];

const scrubber = (shown: number) => {
  const props = { onShow: vi.fn(), onRestore: vi.fn(), onCompare: vi.fn() };
  const view = render(<VersionScrubber versions={versions} shown={shown} {...props} />);
  return { ...props, view, list: screen.getByRole("list", { name: "Version history" }) };
};

it("shows one tick per version, newest first in the list, with its origin, prompt and change count", () => {
  const { list } = scrubber(3);
  expect([...list.querySelectorAll("strong")].map((s) => s.textContent)).toEqual(["v3", "v2", "v1"]);
  const [v3, , v1] = within(list).getAllByRole("listitem");
  expect(v3).toHaveTextContent("refine");
  expect(v3).toHaveTextContent("make it 10 mm thicker");
  expect(v3).toHaveTextContent("0 parameters changed");
  expect(v3?.dataset.agent).toBe("true");
  expect(v1?.querySelector("img")).toHaveAttribute("src", "/models/m1/versions/1/thumbnail");
  expect(within(list).getByRole("button", { current: true })).toHaveTextContent("v3");
  expect(screen.queryByText(/^Viewing/)).toBeNull();
});

it("previews on click and steps with the keys", () => {
  const { list, onShow } = scrubber(2);
  fireEvent.click(within(list).getByRole("button", { name: "v1" }));
  expect(onShow).toHaveBeenLastCalledWith(1);
  const shown = within(list).getByRole("button", { current: true });
  for (const [key, n] of [
    ["[", 1],
    ["]", 3],
    ["ArrowLeft", 1],
    ["Home", 1],
    ["End", 3],
  ] as const) {
    fireEvent.keyDown(shown, { key });
    expect(onShow).toHaveBeenLastCalledWith(n);
  }
});

it("restores the previewed version as a new one or goes back to the latest", () => {
  const { onRestore, onShow } = scrubber(1);
  expect(screen.getByText("Viewing v1")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Restore v1 as v4" }));
  expect(onRestore).toHaveBeenCalledWith(1);
  fireEvent.click(screen.getByRole("button", { name: "Back to v3" }));
  expect(onShow).toHaveBeenCalledWith(3);
});

it("compares the shown version with a picked one as a parameter diff", () => {
  const { list, onCompare, onShow } = scrubber(3);
  fireEvent.click(screen.getByRole("button", { name: "Compare" }));
  expect(screen.getByText("Pick a version to compare with")).toBeInTheDocument();
  fireEvent.click(within(list).getByRole("button", { name: "v1" }));
  expect(onShow).not.toHaveBeenCalled();
  expect(onCompare).toHaveBeenCalledWith([3, 1]);
  const rows = within(screen.getByRole("table", { name: "Parameter diff" })).getAllByRole("row");
  expect(rows.map((r) => r.textContent)).toEqual(["Parameterv3v1", "Plate Length130.00120.00 mm"]);
  fireEvent.click(screen.getByRole("button", { name: "Compare" }));
  expect(onCompare).toHaveBeenLastCalledWith(undefined);
  expect(screen.queryByRole("table")).toBeNull();
});

const suggestion = (id: string, change: Record<string, number>): Suggestion => ({
  id,
  target: "plate",
  change,
  rationale: "keep 1.5 x its diameter from the edge",
  status: "open",
});

it("applies a proposal as a job and dismisses another without one", async () => {
  let open = [suggestion("s1", { plate_length: 140 }), suggestion("s2", { plate_length: 110 })];
  vi.spyOn(api, "versions").mockResolvedValue(versions);
  vi.spyOn(api, "suggestions").mockImplementation(async () => open);
  const accept = vi.spyOn(api, "acceptSuggestion").mockImplementation(async (_, id) => {
    open = open.filter((s) => s.id !== id);
    return { id: "params-1" } as Job;
  });
  const ignore = vi.spyOn(api, "ignoreSuggestion").mockImplementation(async (_, id) => {
    open = open.filter((s) => s.id !== id);
    return suggestion(id, {});
  });
  const onApplied = vi.fn();
  render(<Proposals modelId="m1" onApplied={onApplied} />);
  const region = screen.getByRole("region", { name: "Suggestions" });
  expect(await within(region).findByText("~ Plate Length 130.00 → 140.00 mm")).toBeInTheDocument();

  fireEvent.click(within(region).getAllByRole("button", { name: "Dismiss" })[1] as HTMLElement);
  await waitFor(() => expect(within(region).getAllByRole("listitem")).toHaveLength(1));
  expect(ignore).toHaveBeenCalledWith("m1", "s2");
  expect(onApplied).not.toHaveBeenCalled();

  fireEvent.click(within(region).getByRole("button", { name: "Apply" }));
  expect(await within(region).findByText("No open suggestions.")).toBeInTheDocument();
  expect(accept).toHaveBeenCalledWith("m1", "s1");
  expect(onApplied).toHaveBeenCalledWith({ id: "params-1" });
});
