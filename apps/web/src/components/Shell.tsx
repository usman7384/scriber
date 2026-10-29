import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router";
import { apiUrl } from "../api";
import { initialTheme, type ThemeState } from "../theme";

export function Shell() {
  const [theme, setTheme] = useState(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <img src="/favicon.svg" alt="" width={24} height={24} />
          Partwright
        </Link>
        <nav aria-label="Main">
          <NavLink to="/" end>
            Projects
          </NavLink>
          <NavLink to="/library">Library</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/help">Help</NavLink>
          <a href={apiUrl("/docs")} target="_blank" rel="noreferrer">
            API
          </a>
        </nav>
      </header>
      <main className="page">
        <Outlet context={[theme, setTheme] satisfies ThemeState} />
      </main>
    </div>
  );
}
