import { useMemo, useState, type KeyboardEvent } from "react";
import type { GraphView as Graph } from "../api";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { cx } from "../ui/cx";
import { frame, layoutGraph } from "./graph-layout";

const tones = ["--accent", "--warn", "--pass", "--axis-z", "--fail", "--axis-x", "--muted"];

export function GraphView({ graph }: { graph: Graph }) {
  const [full, setFull] = useState(false);
  const t = useT().graph;
  const { nodes, edges } = useMemo(() => layoutGraph(graph), [graph]);
  const types = [...new Set(nodes.map((n) => n.type))];
  const tone = (type: string) => `var(${tones[types.indexOf(type) % tones.length]})`;
  const box = full ? frame(nodes, innerWidth / 3, innerHeight / 3) : frame(nodes, 100, 100);
  // The preview fits the whole graph, so its dots grow with it; fullscreen keeps about 3 px per unit.
  const r = full ? 3 : Math.max(box[2], box[3]) / 40;
  // Esc leaves fullscreen without also closing the sheet around it.
  const escape = (e: KeyboardEvent) => {
    if (!full || e.key !== "Escape") return;
    e.preventDefault();
    e.stopPropagation();
    setFull(false);
  };

  return (
    <section className={cx("src-graph", full && "fullscreen")} aria-label={t.region} onKeyDown={escape}>
      <header className="src-section-head">
        <h3 className="eyebrow">{t.region}</h3>
        <span className="src-graph-counts mono">{t.counts(nodes.length, edges.length)}</span>
        <Button variant="ghost" onClick={() => setFull(!full)}>
          {full ? t.exit : t.full}
        </Button>
      </header>
      <svg viewBox={box.join(" ")} role="img" aria-label={t.image(nodes.length)}>
        {edges.map(({ a, b }, i) => (
          <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="edge" />
        ))}
        {nodes.map((n) => (
          <g key={n.id} className="src-node">
            <circle cx={n.x} cy={n.y} r={r} style={{ fill: tone(n.type) }} className="node">
              <title>{`${n.type}: ${n.name}`}</title>
            </circle>
            <text x={n.x + 1.6 * r} y={n.y + 0.5 * r} fontSize={1.5 * r}>
              {n.name}
            </text>
          </g>
        ))}
      </svg>
      <ul className="src-legend">
        {types.map((type) => (
          <li key={type}>
            <span className="src-dot" style={{ background: tone(type) }} /> {type}
          </li>
        ))}
      </ul>
    </section>
  );
}
