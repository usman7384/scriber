import { useMemo, useState } from "react";
import type { GraphView } from "../api";
import { useT } from "../i18n";
import { layoutGraph } from "./graph-layout";

const palette = ["#3b82f6", "#f0883e", "#22a06b", "#a371f7", "#e5534b", "#d4a72c", "#39c5cf"];

export function GraphPanel({ graph }: { graph: GraphView }) {
  const [full, setFull] = useState(false);
  const t = useT().graph;
  const { nodes, edges } = useMemo(() => layoutGraph(graph), [graph]);
  const types = [...new Set(nodes.map((n) => n.type))];
  const color = (type: string) => palette[types.indexOf(type) % palette.length];
  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const pad = 20;
  const box = nodes.length
    ? [
        Math.min(...xs) - pad,
        Math.min(...ys) - pad,
        Math.max(...xs) - Math.min(...xs) + 2 * pad,
        Math.max(...ys) - Math.min(...ys) + 2 * pad,
      ]
    : [-50, -50, 100, 100];

  return (
    <section
      className={`panel graph${full ? " fullscreen" : ""}`}
      aria-label={t.region}
      onKeyDown={(e) => e.key === "Escape" && setFull(false)}
    >
      <header className="row">
        <h2>{t.region}</h2>
        <span className="muted small">{t.counts(nodes.length, edges.length)}</span>
        <button type="button" className="secondary small push" onClick={() => setFull(!full)}>
          {full ? t.exit : t.full}
        </button>
      </header>
      <ul className="legend">
        {types.map((t) => (
          <li key={t}>
            <span className="dot" style={{ background: color(t) }} /> {t}
          </li>
        ))}
      </ul>
      <svg viewBox={box.join(" ")} role="img" aria-label={t.image(nodes.length)}>
        {edges.map(({ a, b }, i) => (
          <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="edge" />
        ))}
        {nodes.map((n) => (
          <circle key={n.id} cx={n.x} cy={n.y} r={5} fill={color(n.type)} className="node">
            <title>{`${n.type}: ${n.name}`}</title>
          </circle>
        ))}
      </svg>
    </section>
  );
}
