import type { KbStats } from "../api";
import { useT } from "../i18n";

export function KbStatsCard({ stats }: { stats: KbStats }) {
  const t = useT().kb;
  const values = [
    stats.files,
    stats.facts,
    stats.rules,
    stats.entities,
    stats.relations,
    stats.generations,
    stats.used_in_generation,
  ];
  return (
    <section className="panel" aria-label={t.region}>
      <header className="row">
        <h2>{t.level(stats.level)}</h2>
        <span className="muted small push">{t.score(stats.score, stats.next_level_score)}</span>
      </header>
      <progress value={stats.score} max={stats.next_level_score} aria-label={t.progress} />
      <dl className="stats">
        {t.items.map((label, i) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{values[i]}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
