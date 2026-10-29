import { createContext, useContext } from "react";
import type { ThemePref } from "../theme";

export interface BugTarget {
  modelId: string;
  version: number;
  screenshot: () => string | undefined;
}

export interface ShellApi {
  theme: ThemePref;
  setTheme: (pref: ThemePref) => void;
  openPalette: (query?: string) => void;
  reportBug: (target: BugTarget) => void;
}

export const ShellContext = createContext<ShellApi | null>(null);

export const useShell = () => {
  const shell = useContext(ShellContext);
  if (!shell) throw new Error("useShell needs the ShellProvider");
  return shell;
};
