import { useOutletContext } from "react-router";

export type Theme = "light" | "dark";
export type ThemeState = [Theme, (t: Theme) => void];

export const initialTheme = (): Theme => {
  const saved = localStorage.getItem("theme");
  if (saved === "light" || saved === "dark") return saved;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

export const useTheme = () => useOutletContext<ThemeState>();
