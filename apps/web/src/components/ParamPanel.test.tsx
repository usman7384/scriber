import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { param } from "../test-utils";
import { ParamPanel } from "./ParamPanel";

const params = [
  param(),
  param({ name: "plate_width", label: "Plate Width", value: 80, provenance: { source: "default" } }),
];

describe("ParamPanel", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("shows one row per parameter with slider, field, unit and provenance", () => {
    render(<ParamPanel params={params} busy={false} onApply={vi.fn()} />);
    expect(screen.getByLabelText("Plate Length")).toHaveValue(120);
    expect(screen.getByLabelText("Plate Width slider")).toHaveValue("80");
    expect(screen.getAllByText("mm")).toHaveLength(2);
    expect(screen.getByRole("tooltip", { hidden: true, name: /Plate size 120/ })).toBeInTheDocument();
  });

  it("waits for Apply when apply-instantly is off", () => {
    const onApply = vi.fn();
    render(<ParamPanel params={params} busy={false} onApply={onApply} />);
    fireEvent.change(screen.getByLabelText("Plate Length slider"), { target: { value: "130" } });
    act(() => vi.advanceTimersByTime(2000));
    expect(onApply).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(onApply).toHaveBeenCalledExactlyOnceWith({ plate_length: 130 });
  });

  it("applies on Enter in the numeric field when apply-instantly is off", () => {
    const onApply = vi.fn();
    render(<ParamPanel params={params} busy={false} onApply={onApply} />);
    const field = screen.getByLabelText("Plate Width");
    fireEvent.change(field, { target: { value: "90" } });
    fireEvent.submit(field);
    expect(onApply).toHaveBeenCalledExactlyOnceWith({ plate_width: 90 });
  });

  it("applies once after the debounce when apply-instantly is on", () => {
    const onApply = vi.fn();
    render(<ParamPanel params={params} busy={false} onApply={onApply} />);
    fireEvent.click(screen.getByLabelText("Apply instantly"));
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
