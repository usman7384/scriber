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
