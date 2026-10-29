import { useEffect, useState } from "react";

export type Theme = "light" | "dark";
export type ThemePref = "system" | Theme;

export const themePrefs: ThemePref[] = ["system", "light", "dark"];

export const resolveTheme = (pref: ThemePref, systemDark: boolean): Theme =>
  pref === "system" ? (systemDark ? "dark" : "light") : pref;

export const initialThemePref = (): ThemePref => {
  const saved = localStorage.getItem("theme");
  return saved === "light" || saved === "dark" ? saved : "system";
};

const darkQuery = () => matchMedia("(prefers-color-scheme: dark)");

// "system" is resolved here so tokens.css only ever sees data-theme light or dark.
export function useThemePref() {
  const [pref, setPref] = useState(initialThemePref);
  const [systemDark, setSystemDark] = useState(() => darkQuery().matches);
  useEffect(() => {
    const query = darkQuery();
    const sync = () => setSystemDark(query.matches);
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = resolveTheme(pref, systemDark);
    localStorage.setItem("theme", pref);
  }, [pref, systemDark]);
  return [pref, setPref] as const;
}
