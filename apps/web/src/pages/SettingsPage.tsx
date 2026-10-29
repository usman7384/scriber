import { API_BASE } from "../api";
import { useTheme, type Theme } from "../theme";

const themes: Theme[] = ["light", "dark"];

export function SettingsPage() {
  const [theme, setTheme] = useTheme();
  return (
    <section className="stack narrow">
      <h1>Settings</h1>
      <fieldset className="panel">
        <legend>Theme</legend>
        {themes.map((t) => (
          <label key={t} className="toggle">
            <input type="radio" name="theme" checked={theme === t} onChange={() => setTheme(t)} />
            {t === "light" ? "Light" : "Dark"}
          </label>
        ))}
      </fieldset>
      <section className="panel" aria-label="API server">
        <h2>API server</h2>
        <p>
          <code>{API_BASE || window.location.origin}</code>
        </p>
        <p className="muted small">
          Set with VITE_API_URL at build time. Every request goes to this server only.
        </p>
      </section>
    </section>
  );
}
