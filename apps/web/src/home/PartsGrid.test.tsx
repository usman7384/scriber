import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it } from "vitest";
import { PartsGrid, type Part } from "./PartsGrid";

const part = (id: string, title: string, created: string): Part => ({
  id,
  title,
  created,
  thumbnail: `/thumbs/${id}.png`,
  href: `/m/${id}`,
  meta: <p>v1</p>,
});

const parts = [
  part("a", "Spacer", "2026-10-27T08:00:00Z"),
  part("b", "Bracket", "2026-10-26T08:00:00Z"),
  { ...part("c", "Plate", "2026-10-25T08:00:00Z"), thumbnail: null },
];

const grid = () =>
  render(
    <MemoryRouter>
      <PartsGrid label="Models" parts={parts} empty="No models yet." />
    </MemoryRouter>,
  );

it("lists parts newest first, each linking to its model with its thumbnail", () => {
  grid();
  const links = within(screen.getByRole("list", { name: "Models" })).getAllByRole("link");
  expect(links.map((l) => l.textContent)).toEqual(["Spacer", "Bracket", "Plate"]);
  expect(links[0]).toHaveAttribute("href", "/m/a");
  expect(screen.getAllByRole("listitem")[0]?.querySelector("img")).toHaveAttribute("src", "/thumbs/a.png");
  expect(screen.getAllByRole("listitem")[2]?.querySelector("img")).toBeNull();
});

it("sorts by name on request", () => {
  grid();
  fireEvent.change(screen.getByLabelText("Sort parts"), { target: { value: "name" } });
  expect(screen.getAllByRole("link").map((l) => l.textContent)).toEqual(["Bracket", "Plate", "Spacer"]);
});

it("says what to do when there are no parts", () => {
  render(
    <MemoryRouter>
      <PartsGrid label="Models" parts={[]} empty="No models yet." />
    </MemoryRouter>,
  );
  expect(screen.getByText("No models yet.")).toBeInTheDocument();
  expect(screen.queryByRole("list")).toBeNull();
});
