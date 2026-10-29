import { forceCenter, forceLink, forceManyBody, forceSimulation, type SimulationNodeDatum } from "d3-force";
import type { GraphView } from "../api";

export interface PlacedNode extends SimulationNodeDatum {
  id: string;
  type: string;
  name: string;
  x: number;
  y: number;
}

export function layoutGraph(graph: GraphView) {
  const nodes = graph.nodes.map((n, i): PlacedNode => ({ ...n, x: Math.cos(i) * i, y: Math.sin(i) * i }));
  const at = new Map(nodes.map((n) => [n.id, n]));
  const links = graph.edges
    .filter((e) => at.has(e.src) && at.has(e.dst))
    .map((e) => ({ source: e.src, target: e.dst }));
  forceSimulation(nodes)
    .force(
      "link",
      forceLink<PlacedNode, (typeof links)[number]>(links)
        .id((n) => n.id)
        .distance(40),
    )
    .force("charge", forceManyBody().strength(-60))
    .force("center", forceCenter(0, 0))
    .stop()
    .tick(300);
  const edges = graph.edges.flatMap((e) => {
    const a = at.get(e.src);
    const b = at.get(e.dst);
    return a && b ? [{ a, b }] : [];
  });
  return { nodes, edges };
}

// A viewBox around the nodes, at least min wide and high, so nodes keep a sane size on a big screen.
export function frame(nodes: PlacedNode[], minWidth: number, minHeight: number) {
  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const [x0, x1, y0, y1] = nodes.length
    ? [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
    : [0, 0, 0, 0];
  const width = Math.max(x1 - x0 + 40, minWidth);
  const height = Math.max(y1 - y0 + 40, minHeight);
  return [(x0 + x1 - width) / 2, (y0 + y1 - height) / 2, width, height] as const;
}
