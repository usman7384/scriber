import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router";
import { apiUrl } from "../api";
import { initialLang, LangContext, messages, type Lang } from "../i18n";
import { initialTheme, type ThemeState } from "../theme";

export function Shell() {
  const [theme, setTheme] = useState(initialTheme);
  const [lang, setLang] = useState(initialLang);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);
  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem("lang", lang);
  }, [lang]);
  const t = messages[lang];
  return (
    <LangContext value={[lang, setLang]}>
      <div className="shell">
        <header className="topbar">
          <Link to="/" className="brand">
            <img src="/favicon.svg" alt="" width={24} height={24} />
            Partwright
          </Link>
          <nav aria-label={t.nav.main}>
            <NavLink to="/" end>
              {t.nav.projects}
            </NavLink>
            <NavLink to="/library">{t.nav.library}</NavLink>
            <NavLink to="/settings">{t.nav.settings}</NavLink>
            <NavLink to="/help">{t.nav.help}</NavLink>
            <a href={apiUrl("/docs")} target="_blank" rel="noreferrer">
              {t.nav.api}
            </a>
          </nav>
          <select aria-label={t.language} value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
            {(Object.keys(messages) as Lang[]).map((l) => (
              <option key={l} value={l}>
                {t.languages[l]}
              </option>
            ))}
          </select>
        </header>
        <main className="page">
          <Outlet context={[theme, setTheme] satisfies ThemeState} />
        </main>
      </div>
    </LangContext>
  );
}
