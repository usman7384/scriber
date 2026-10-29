import { Link } from "react-router";
import { useT } from "../i18n";

export function HelpPage() {
  const { help: t, nav } = useT();
  const sections: [string, string][] = [
    [t.change, t.changeText],
    [t.context, t.contextText],
    [t.files, t.filesText],
  ];
  return (
    <section className="stack narrow">
      <h1>{t.title}</h1>
      <section className="panel">
        <h2>{t.make}</h2>
        <p>
          {t.makeBefore}
          <Link to="/">{nav.projects}</Link>
          {t.makeAfter}
        </p>
      </section>
      {sections.map(([title, text]) => (
        <section key={title} className="panel">
          <h2>{title}</h2>
          <p>{text}</p>
        </section>
      ))}
    </section>
  );
}
