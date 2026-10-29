import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation } from "react-router";
import { initialLang, LangContext, type Lang } from "../i18n";
import { useThemePref } from "../theme";
import { ActionsContext, createRegistry } from "./actions";
import { BugSheet } from "./BugSheet";
import { useBuiltInActions } from "./builtins";
import { ShellContext, type BugTarget, type ShellApi } from "./context";
import { useShortcutLayer } from "./keys";
import { Palette } from "./palette/Palette";

// Theme, language, the action registry, the palette and the bug sheet, for every route.
export function ShellProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useThemePref();
  const [lang, setLang] = useState(initialLang);
  const [registry] = useState(createRegistry);
  const [palette, setPalette] = useState<string>();
  const [bug, setBug] = useState<BugTarget>();
  const { pathname } = useLocation();

  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem("lang", lang);
  }, [lang]);
  useBuiltInActions(registry, setTheme, setLang);
  useShortcutLayer(
    registry,
    () => ({ pathname, query: "" }),
    () => setPalette((open) => (open === undefined ? "" : undefined)),
  );

  const langState = useMemo((): [Lang, (l: Lang) => void] => [lang, setLang], [lang]);
  const shell = useMemo(
    (): ShellApi => ({ theme, setTheme, openPalette: (query = "") => setPalette(query), reportBug: setBug }),
    [theme, setTheme],
  );
  return (
    <LangContext value={langState}>
      <ActionsContext value={registry}>
        <ShellContext value={shell}>
          {children}
          <Palette query={palette} onClose={() => setPalette(undefined)} />
          {bug && <BugSheet target={bug} onClose={() => setBug(undefined)} />}
        </ShellContext>
      </ActionsContext>
    </LangContext>
  );
}
