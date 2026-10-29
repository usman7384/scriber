import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it } from "vitest";
import type { Model } from "../api";
import { ModelGallery } from "./ModelGallery";

const model = (id: string, title: string, created: string): Model => ({
  id,
  project_id: "p1",
  title,
  created,
  latest_version: 1,
  versions: 1,
  thumbnail_url: `/thumbs/${id}.png`,
});

it("lists models newest first with thumbnail and title", () => {
  render(
    <MemoryRouter>
      <ModelGallery
        models={[
          model("a", "Spacer", "2026-10-24T08:00:00Z"),
          model("b", "Bracket", "2026-10-26T08:00:00Z"),
          model("c", "Plate", "2026-10-25T08:00:00Z"),
        ]}
      />
    </MemoryRouter>,
  );
  const links = screen.getAllByRole("link");
  expect(links.map((l) => l.textContent)).toEqual(["Bracket", "Plate", "Spacer"]);
  expect(links[0]).toHaveAttribute("href", "/m/b");
  expect(links[0]?.querySelector("img")).toHaveAttribute("src", "/thumbs/b.png");
});

it("says when a model has no version yet", () => {
  render(
    <MemoryRouter>
      <ModelGallery
        models={[
          { ...model("a", "Pending part", "2026-10-26T08:00:00Z"), latest_version: null, versions: 0 },
        ]}
      />
    </MemoryRouter>,
  );
  expect(screen.getByText(/no version yet/)).toBeInTheDocument();
});

it("shows where a forked model came from", () => {
  const forked_from = { publication: "c1", model_id: "m2", version: 2, title: "Edge plate", author: "alice" };
  render(
    <MemoryRouter>
      <ModelGallery models={[{ ...model("a", "Edge plate", "2026-10-26T08:00:00Z"), forked_from }]} />
    </MemoryRouter>,
  );
  expect(screen.getByText("Forked from Edge plate v2 by alice")).toBeInTheDocument();
});
