import { useEffect, useState } from "react";
import { Link, NavLink, Outlet } from "react-router";
import { apiUrl } from "../api";

type Theme = "light" | "dark";

const initialTheme = (): Theme => {
  const saved = localStorage.getItem("theme");
  if (saved === "light" || saved === "dark") return saved;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

export function Shell() {
  const [theme, setTheme] = useState(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);
  const other = theme === "dark" ? "light" : "dark";
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
          <a href={apiUrl("/docs")} target="_blank" rel="noreferrer">
            API
          </a>
        </nav>
        <button type="button" className="ghost" onClick={() => setTheme(other)}>
          {other === "dark" ? "Dark" : "Light"} theme
        </button>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  );
}
