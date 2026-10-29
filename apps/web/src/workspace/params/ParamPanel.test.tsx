import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { param } from "../../test-utils";
import { ParamPanel } from "./ParamPanel";

const params = [
  param(),
  param({
    name: "thickness",
    label: "Thickness",
    value: 6,
    min: 3,
    max: 20,
    provenance: { source: "default" },
  }),
];

describe("ParamPanel", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("shows one row per parameter with slider, field, unit, bounds and provenance", () => {
    render(<ParamPanel params={params} busy={false} onApply={vi.fn()} />);
    expect(screen.getByLabelText("Plate Length")).toHaveValue(120);
    expect(screen.getByLabelText("Thickness slider")).toHaveValue("6");
    expect(screen.getByLabelText("Thickness slider")).toHaveAttribute("min", "3");
    expect(screen.getAllByText("mm")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Source of Plate Length: document" })).toHaveTextContent("DOC");
    expect(screen.getByText("Plate size 120 x 80 x 6 mm")).toBeInTheDocument();
    expect(screen.getByText("DEF")).toHaveAttribute("data-assumed");
  });

  it("waits for Apply when Live is off and counts the changes", () => {
    const onApply = vi.fn();
    render(<ParamPanel params={params} busy={false} onApply={onApply} />);
    expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Plate Length slider"), { target: { value: "130" } });
    act(() => vi.advanceTimersByTime(2000));
    expect(onApply).not.toHaveBeenCalled();
    expect(screen.getByText("was 120.00 mm")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apply 1 change" }));
    expect(onApply).toHaveBeenCalledExactlyOnceWith({ plate_length: 130 });
  });

  it("applies on Enter in the numeric field and resets drafts", () => {
    const onApply = vi.fn();
    render(<ParamPanel params={params} busy={false} onApply={onApply} />);
    const field = screen.getByLabelText("Thickness");
    fireEvent.change(field, { target: { value: "9" } });
    fireEvent.submit(field);
    expect(onApply).toHaveBeenCalledExactlyOnceWith({ thickness: 9 });
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(field).toHaveValue(6);
  });

  it("names the bound and holds the change while a value is out of bounds", () => {
    const onApply = vi.fn();
    render(<ParamPanel params={params} busy={false} onApply={onApply} />);
    const field = screen.getByLabelText("Thickness");
    fireEvent.change(field, { target: { value: "25" } });
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAccessibleDescription("Above the maximum of 20.00 mm");
    fireEvent.submit(field);
    expect(onApply).not.toHaveBeenCalled();
  });

  it("steps with the arrow keys: Shift x10, Alt x0.1", () => {
    render(<ParamPanel params={params} busy={false} onApply={vi.fn()} />);
    const field = screen.getByLabelText("Thickness");
    fireEvent.keyDown(field, { key: "ArrowUp" });
    expect(field).toHaveValue(7);
    fireEvent.keyDown(field, { key: "ArrowDown", shiftKey: true });
    expect(field).toHaveValue(-3);
    fireEvent.keyDown(screen.getByLabelText("Thickness slider"), { key: "ArrowLeft", altKey: true });
    expect(field).toHaveValue(3);
  });

  it("pins the driving parameter on top", () => {
    render(<ParamPanel params={params} pinned="thickness" busy={false} onApply={vi.fn()} />);
    expect(screen.getAllByRole("spinbutton").map((f) => f.id)).toEqual([
      "param-thickness",
      "param-plate_length",
    ]);
  });

  it("applies once after the debounce when Live is on", () => {
    const onApply = vi.fn();
    render(<ParamPanel params={params} busy={false} onApply={onApply} />);
    fireEvent.click(screen.getByRole("switch", { name: "Apply instantly" }));
    expect(screen.queryByRole("button", { name: "Apply" })).not.toBeInTheDocument();
    const slider = screen.getByLabelText("Plate Length slider");
    fireEvent.change(slider, { target: { value: "125" } });
    act(() => vi.advanceTimersByTime(200));
    fireEvent.change(slider, { target: { value: "140" } });
    act(() => vi.advanceTimersByTime(200));
    expect(onApply).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(300));
    expect(onApply).toHaveBeenCalledExactlyOnceWith({ plate_length: 140 });
  });
});
