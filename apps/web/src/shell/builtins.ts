import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router";
import { apiUrl } from "../api";
import { messages, type Lang } from "../i18n";
import { themePrefs, type ThemePref } from "../theme";
import type { Action, ActionRegistry } from "./actions";
import { useOpenSheet } from "./sheets";

const langs = Object.keys(messages) as Lang[];

export function useBuiltInActions(
  registry: ActionRegistry,
  setTheme: (pref: ThemePref) => void,
  setLang: (lang: Lang) => void,
) {
  const navigate = useNavigate();
  const openSheet = useOpenSheet();
  const actions = useMemo<Action[]>(
    () => [
      {
        id: "go.home",
        group: "navigate",
        icon: "grid",
        label: (t) => t.nav.projects,
        run: () => navigate("/"),
      },
      {
        id: "go.library",
        group: "navigate",
        icon: "part",
        label: (t) => t.nav.library,
        run: () => navigate("/library"),
      },
      {
        id: "go.explore",
        group: "navigate",
        icon: "globe",
        label: (t) => t.nav.community,
        run: () => navigate("/explore"),
      },
      {
        id: "settings.open",
        group: "settings",
        icon: "settings",
        label: (t) => t.settings.title,
        run: () => openSheet("settings"),
      },
      ...themePrefs.map((pref): Action => ({
        id: `settings.theme.${pref}`,
        group: "settings",
        icon: "eye",
        label: (t) => `${t.settings.theme}: ${t.settings[pref]}`,
        run: () => setTheme(pref),
      })),
      ...langs.map((lang): Action => ({
        id: `settings.lang.${lang}`,
        group: "settings",
        icon: "globe",
        label: (t) => `${t.language}: ${t.languages[lang]}`,
        run: () => setLang(lang),
      })),
      {
        id: "help.open",
        group: "help",
        icon: "help",
        shortcut: "?",
        label: (t) => t.help.title,
        run: () => openSheet("help"),
      },
      {
        id: "help.api",
        group: "help",
        icon: "document",
        label: (t) => t.nav.api,
        run: () => window.open(apiUrl("/docs"), "_blank", "noreferrer"),
      },
    ],
    [navigate, openSheet, setTheme, setLang],
  );
  useEffect(() => registry.add(actions), [registry, actions]);
}
