// Mounts the agent I/O components on their own until the workspace and home pages take them (UI_DIRECTION §7).
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { LangContext, type Lang } from "../../src/i18n";
import "../../src/styles/fonts.css";
import "../../src/styles/tokens.css";
import "../../src/styles/base.css";
import "../../src/styles/app.css";
import { Home, Workspace } from "./Harness";

const query = new URLSearchParams(location.search);
const lang: Lang = query.get("lang") === "de" ? "de" : "en";
document.documentElement.dataset.theme = query.get("theme") === "light" ? "light" : "dark";
document.documentElement.lang = lang;

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <BrowserRouter>
      <LangContext value={[lang, () => undefined]}>
        {query.get("view") === "workspace" ? <Workspace /> : <Home />}
      </LangContext>
    </BrowserRouter>
  </StrictMode>,
);
