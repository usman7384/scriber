import { useT } from "../i18n";
import { useShell } from "./context";
import { isMac, keyCaps, PALETTE_KEY } from "./keys";
import { Icon } from "../ui/icons";
import { Kbd } from "../ui/Kbd";

export function SearchButton({ label }: { label: string }) {
  const { openPalette } = useShell();
  const t = useT();
  return (
    <button
      type="button"
      className="shell-search"
      aria-keyshortcuts="Control+K"
      onClick={() => openPalette()}
    >
      <Icon name="search" />
      <span className="shell-label">{label}</span>
      <span aria-hidden="true" className="shell-search-keys">
        <Kbd keys={keyCaps(PALETTE_KEY, isMac(), t.agent.command.ctrl)} />
      </span>
    </button>
  );
}
