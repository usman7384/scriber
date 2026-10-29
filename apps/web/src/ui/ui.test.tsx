import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { LangContext } from "../i18n";
import { Button } from "./Button";
import { Chip } from "./Chip";
import { IconButton } from "./IconButton";
import { Icon } from "./icons";
import { Kbd } from "./Kbd";
import { Popover } from "./Popover";
import { Provenance } from "./Provenance";
import { Sheet } from "./Sheet";
import { Status } from "./Status";
import { Tooltip } from "./Tooltip";

// jsdom has neither modal dialogs nor the popover API.
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
  HTMLElement.prototype.togglePopover = function (force?: boolean) {
    return this.toggleAttribute("data-open", force);
  };
});

describe("Button", () => {
  it("is a plain button by default and carries its variant and icon", () => {
    render(
      <Button variant="primary" icon="send">
        Generate
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Generate" });
    expect(button).toHaveAttribute("type", "button");
    expect(button).toHaveAttribute("data-variant", "primary");
    expect(button.querySelector("[data-icon=send]")).toBeInTheDocument();
  });
});

describe("IconButton", () => {
  it("is named by its label and shows the same label as a tooltip on focus", async () => {
    render(<IconButton icon="search" label="Search" />);
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Search" })).toHaveFocus();
    const tip = screen.getByText("Search");
    expect(tip).toHaveAttribute("data-open");
    expect(tip).toHaveAttribute("aria-hidden", "true");
  });
});

describe("Tooltip", () => {
  it("describes its trigger, opens on hover and focus, and closes on Esc", async () => {
    render(
      <Tooltip text="Plate size 120 x 80 x 6 mm">
        <button type="button">DOC</button>
      </Tooltip>,
    );
    const trigger = screen.getByRole("button", { name: "DOC" });
    expect(trigger).toHaveAccessibleDescription("Plate size 120 x 80 x 6 mm");
    await userEvent.hover(trigger);
    const tip = screen.getByRole("tooltip", { hidden: true });
    expect(tip).toHaveAttribute("data-open");
    await userEvent.unhover(trigger);
    expect(tip).not.toHaveAttribute("data-open");
    await userEvent.tab();
    expect(tip).toHaveAttribute("data-open");
    await userEvent.keyboard("{Escape}");
    expect(tip).not.toHaveAttribute("data-open");
  });
});

describe("Chip", () => {
  it("truncates with a title and offers a named remove button", async () => {
    const onClick = vi.fn();
    render(<Chip remove={{ label: "Remove spec.pdf", onClick }}>spec.pdf</Chip>);
    expect(screen.getByText("spec.pdf")).toHaveAttribute("title", "spec.pdf");
    await userEvent.click(screen.getByRole("button", { name: "Remove spec.pdf" }));
    expect(onClick).toHaveBeenCalledOnce();
  });
});

describe("Kbd", () => {
  it("renders one key cap per key", () => {
    const { container } = render(<Kbd keys={["Ctrl", "K"]} />);
    expect([...container.querySelectorAll("kbd")].map((k) => k.textContent)).toEqual(["Ctrl", "K"]);
  });
});

describe("Status", () => {
  it("pairs a glyph with a word, in the chosen language", () => {
    const { container } = render(
      <LangContext value={["de", () => undefined]}>
        <Status state="warn" />
      </LangContext>,
    );
    expect(container.querySelector("[data-icon=warn]")).toBeInTheDocument();
    expect(screen.getByText("Warnung")).toHaveAttribute("data-state", "warn");
  });
});

describe("Provenance", () => {
  it("shows a monogram, names the source, and flags defaults as assumptions", () => {
    render(
      <>
        <Provenance source="document" />
        <Provenance source="default" />
      </>,
    );
    expect(screen.getByText("DOC")).toHaveAttribute("title", "document");
    expect(screen.getByText("DOC")).not.toHaveAttribute("data-assumed");
    expect(screen.getByText("DEF")).toHaveAttribute("data-assumed");
  });
});

describe("Popover", () => {
  it("wires its trigger to a labelled native popover and tracks open state", () => {
    render(
      <Popover label="Checks" trigger={(p) => <Button {...p}>3 checks</Button>}>
        <p>All requirements pass</p>
      </Popover>,
    );
    const trigger = screen.getByRole("button", { name: "3 checks" });
    const panel = document.getElementById(trigger.getAttribute("popovertarget") ?? "") as HTMLElement;
    expect(panel).toHaveAttribute("role", "dialog");
    expect(panel).toHaveAttribute("aria-label", "Checks");
    expect(panel).toHaveAttribute("popover", "auto");
    fireEvent(panel, Object.assign(new Event("toggle"), { newState: "open" }));
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(panel).toHaveAttribute("data-placed");
  });
});

describe("Sheet", () => {
  it("opens as a titled modal dialog and reports a close once", async () => {
    const onClose = vi.fn();
    const { rerender } = render(
      <Sheet open title="Sources" onClose={onClose} footer={<Button>Use 2</Button>}>
        <p>Drop a datasheet</p>
      </Sheet>,
    );
    expect(screen.getByRole("dialog", { name: "Sources" })).toHaveAttribute("open");
    expect(screen.getByRole("button", { name: "Use 2" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledOnce();
    rerender(
      <Sheet open={false} title="Sources" onClose={onClose}>
        <p>Drop a datasheet</p>
      </Sheet>,
    );
    expect(onClose).toHaveBeenCalledOnce();
  });
});

describe("Icon", () => {
  it("is decorative and draws with the current colour", () => {
    const { container } = render(<Icon name="mark" size={24} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).toHaveAttribute("stroke", "currentColor");
    expect(svg).toHaveAttribute("width", "24");
  });
});
