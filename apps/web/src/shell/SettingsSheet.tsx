import { API_BASE } from "../api";
import { useT } from "../i18n";
import { useTheme, type Theme } from "../theme";

const themes: Theme[] = ["light", "dark"];

export function SettingsPage() {
  const [theme, setTheme] = useTheme();
  const t = useT().settings;
  return (
    <section className="stack narrow">
      <h1>{t.title}</h1>
      <fieldset className="panel">
        <legend>{t.theme}</legend>
        {themes.map((mode) => (
          <label key={mode} className="toggle">
            <input type="radio" name="theme" checked={theme === mode} onChange={() => setTheme(mode)} />
            {t[mode]}
          </label>
        ))}
      </fieldset>
      <section className="panel" aria-label={t.server}>
        <h2>{t.server}</h2>
        <p>
          <code>{API_BASE || window.location.origin}</code>
        </p>
        <p className="muted small">{t.serverNote}</p>
      </section>
    </section>
  );
}
