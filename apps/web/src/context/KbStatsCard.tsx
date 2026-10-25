import type { KbStats } from "../api";

export function KbStatsCard({ stats }: { stats: KbStats }) {
  const items: [string, number][] = [
    ["Files", stats.files],
    ["Facts", stats.facts],
    ["Rules", stats.rules],
    ["Entities", stats.entities],
    ["Relations", stats.relations],
    ["Generations", stats.generations],
    ["Used in generation", stats.used_in_generation],
  ];
  return (
    <section className="panel" aria-label="Knowledge base">
      <header className="row">
        <h2>Knowledge base level {stats.level}</h2>
        <span className="muted small push">
          score {stats.score} / {stats.next_level_score}
        </span>
      </header>
      <progress value={stats.score} max={stats.next_level_score} aria-label="Progress to next level" />
      <dl className="stats">
        {items.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
