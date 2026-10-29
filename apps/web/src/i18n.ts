import { createContext, useContext } from "react";
import * as agent from "./i18n/agent";
import * as common from "./i18n/common";
import * as home from "./i18n/home";
import * as shell from "./i18n/shell";
import * as workspace from "./i18n/workspace";

export type Lang = "en" | "de";

// EN and DE spread in the same order: the language spec pairs their strings by position.
const en = { ...common.en, ...shell.en, ...workspace.en, ...agent.en, ...home.en };

export type Messages = typeof en;

const de: Messages = { ...common.de, ...shell.de, ...workspace.de, ...agent.de, ...home.de };

export const messages: Record<Lang, Messages> = { en, de };

export const LangContext = createContext<[Lang, (lang: Lang) => void]>(["en", () => undefined]);

export const useLang = () => useContext(LangContext);

export const useT = () => messages[useContext(LangContext)[0]];

export const initialLang = (): Lang => (localStorage.getItem("lang") === "de" ? "de" : "en");
