import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { version } from "../test-utils";
import { VersionHistory } from "./VersionHistory";

const versions = [version(1, { thumbnail_url: "/thumbs/1.png" }), version(2), version(3)];

it("lists versions newest first with origin, prompt and thumbnail, and restores an older one", () => {
  const onRestore = vi.fn();
  const onSelect = vi.fn();
  render(
    <VersionHistory versions={versions} selected={3} latest={3} onSelect={onSelect} onRestore={onRestore} />,
  );
  const items = screen.getAllByRole("listitem");
  expect(items.map((li) => li.querySelector("strong")?.textContent)).toEqual(["v3", "v2", "v1"]);
  expect(items[2]).toHaveTextContent("generate");
  expect(items[2]).toHaveTextContent("Sensor plate");
  expect(items[2]?.querySelector("img")).toHaveAttribute("src", "/thumbs/1.png");
  expect(screen.queryByRole("button", { name: "Restore v3" })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Restore v1" }));
  expect(onRestore).toHaveBeenCalledExactlyOnceWith(1);
  fireEvent.click(screen.getByRole("button", { name: /^v2/ }));
  expect(onSelect).toHaveBeenCalledWith(2);
});
