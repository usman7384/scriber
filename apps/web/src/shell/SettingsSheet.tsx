import { useId } from "react";
import { API_BASE, apiUrl } from "../api";
import { messages, useLang, useT, type Lang } from "../i18n";
import { themePrefs } from "../theme";
import { Sheet } from "../ui/Sheet";
import { useShell } from "./context";
import { useCloseSheet } from "./sheets";

export function SettingsSheet() {
  const { theme, setTheme } = useShell();
  const [lang, setLang] = useLang();
  const close = useCloseSheet();
  const id = useId();
  const t = useT();
  return (
    <Sheet open onClose={close} title={t.settings.title}>
      <div className="shell-form">
        <fieldset className="shell-fieldset">
          <legend>{t.settings.theme}</legend>
          <div className="shell-segments">
            {themePrefs.map((pref) => (
              <label key={pref}>
                <input type="radio" name="theme" checked={theme === pref} onChange={() => setTheme(pref)} />
                {t.settings[pref]}
              </label>
            ))}
          </div>
        </fieldset>
        <label htmlFor={`${id}-lang`}>{t.language}</label>
        <select id={`${id}-lang`} value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
          {(Object.keys(messages) as Lang[]).map((l) => (
            <option key={l} value={l}>
              {t.languages[l]}
            </option>
          ))}
        </select>
        <section className="shell-server" aria-labelledby={`${id}-server`}>
          <h3 id={`${id}-server`}>{t.settings.server}</h3>
          <code>{API_BASE || window.location.origin}</code>
          <p>{t.settings.serverNote}</p>
          <a href={apiUrl("/docs")} target="_blank" rel="noreferrer">
            {t.nav.api}
          </a>
        </section>
      </div>
    </Sheet>
  );
}
