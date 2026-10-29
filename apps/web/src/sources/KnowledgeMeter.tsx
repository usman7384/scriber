import type { KbStats } from "../api";
import { useT } from "../i18n";

export function KnowledgeMeter({ stats }: { stats: KbStats }) {
  const t = useT().kb;
  const values = [stats.files, stats.facts, stats.rules, stats.used_in_generation];
  return (
    <section className="src-kb" aria-label={t.region}>
      <header>
        <span>{t.level(stats.level)}</span>{" "}
        <progress value={stats.score} max={stats.next_level_score} aria-label={t.progress} />
        <span className="mono">
          {stats.score} / {stats.next_level_score}
        </span>
      </header>
      <dl>
        {t.items.map((label, i) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className="mono">{values[i]}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
