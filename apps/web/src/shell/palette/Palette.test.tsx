import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useMemo } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { beforeAll, beforeEach, expect, it, vi } from "vitest";
import { useRegisterActions, type Action } from "../actions";
import { ShellProvider } from "../ShellProvider";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
  window.matchMedia = vi.fn().mockReturnValue({
    matches: true,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  });
});

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      Response.json(
        url.endsWith("/projects")
          ? [{ id: "p1", name: "Bracket lab" }]
          : [{ id: "m1", title: "Sensor plate" }],
      ),
    ),
  );
});

const setThickness = vi.fn();

function Workspace() {
  const actions = useMemo<Action[]>(
    () => [
      {
        id: "param.thickness",
        group: "parameters",
        label: () => "Thickness",
        param: { name: "plate_thickness", label: "Thickness", value: 6, unit: "mm", min: 3, max: 20 },
        run: setThickness,
      },
    ],
    [],
  );
  useRegisterActions(actions);
  return <p>{useLocation().pathname}</p>;
}

const renderShell = () =>
  render(
    <MemoryRouter initialEntries={["/m/m1"]}>
      <ShellProvider>
        <Routes>
          <Route path="*" element={<Workspace />} />
        </Routes>
      </ShellProvider>
    </MemoryRouter>,
  );

it("opens on Ctrl+K and sets a parameter from name = value", async () => {
  const user = userEvent.setup();
  renderShell();
  await user.keyboard("{Control>}k{/Control}");
  const input = screen.getByRole("combobox", { name: "Search actions, parameters and places" });
  await user.type(input, "thick = 7");
  expect(screen.getByRole("option", { selected: true })).toHaveTextContent(
    "Set Thickness6.00 → 7.00 mm3.00–20.00 mm",
  );
  await user.keyboard("{Enter}");
  expect(setThickness).toHaveBeenCalledWith("7");
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
});

it("refuses a value out of bounds", async () => {
  const user = userEvent.setup();
  renderShell();
  await user.keyboard("{Control>}k{/Control}");
  await user.type(screen.getByRole("combobox"), "thick = 30");
  expect(screen.getByRole("option", { selected: true })).toHaveAttribute("aria-disabled", "true");
  await user.keyboard("{Enter}");
  expect(setThickness).not.toHaveBeenCalledWith("30");
});

it("sets the theme and goes to places it fetched", async () => {
  const user = userEvent.setup();
  renderShell();
  await user.keyboard("{Control>}k{/Control}");
  await user.type(screen.getByRole("combobox"), "theme light");
  await user.keyboard("{Enter}");
  expect(document.documentElement.dataset.theme).toBe("light");

  await user.keyboard("{Control>}k{/Control}");
  await user.type(screen.getByRole("combobox"), "sensor");
  await act(async () => undefined);
  await user.click(await screen.findByRole("option", { name: /Sensor plate/ }));
  expect(screen.getByText("/m/m1")).toBeInTheDocument();
  await user.keyboard("{Control>}k{/Control}");
  await user.type(screen.getByRole("combobox"), "sources");
  await user.click(await screen.findByRole("option", { name: /Sources · Bracket lab/ }));
  expect(screen.getByText("/p/p1/context")).toBeInTheDocument();
});
