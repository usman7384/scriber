import { readFileSync } from "node:fs";
import type { ContextFile, Finding, GraphView, Model, Param, Project, Version } from "../src/api";

export const now = (minute: number) => `2026-10-26T10:${String(minute).padStart(2, "0")}:00Z`;

export const asset = (name: string) => readFileSync(new URL(`./fixtures/${name}`, import.meta.url));

export const project: Project = {
  id: "p1",
  name: "Bracket lab",
  created: now(0),
  model_count: 0,
  file_count: 6,
};

export const shop: Project = {
  id: "p2",
  name: "Fixture shop",
  created: now(2),
  model_count: 2,
  file_count: 0,
};

export const shopModels: Model[] = [
  {
    id: "m2",
    project_id: "p2",
    title: "Edge test plate",
    created: now(3),
    latest_version: 2,
    versions: 2,
    thumbnail_url: "/models/m2/versions/2/thumbnail",
  },
  {
    id: "m3",
    project_id: "p2",
    title: "Hole near edge",
    created: "2026-10-25T09:00:00Z",
    latest_version: 1,
    versions: 1,
    thumbnail_url: "/models/m3/versions/1/thumbnail",
  },
];

export const shopThumbnails: Record<string, Buffer> = {
  m2: asset("edge-plate-x15.png"),
  m3: asset("edge-plate-x20.png"),
};

export interface Built {
  glb: Buffer;
  thumbnail: Buffer;
  findings: Finding[];
}

// A scenario stands in for the geometry service: each parameter set maps to prebuilt real output.
export interface Scenario {
  title: string;
  prompt: string;
  params: Param[];
  checks: Version["checks"];
  volume: number;
  build: (values: Record<string, number>) => Built | undefined;
}

const sensorFinding: Finding = {
  rule_id: "min_hole_edge_ratio",
  severity: "warning",
  binding: "static",
  message: "Hole Ø6.6 is 10 mm from the edge; needs at least 13.2 mm",
  location: { point: [26.85, 16.85, 6], face: null },
  suggestion: "Keep hole centres within x ±46.8 and y ±26.8",
};

export const sensorPlate: Scenario = {
  title: "Sensor plate",
  prompt: "Sensor plate 120 x 80 x 6 mm with four M6 holes",
  params: [
    {
      name: "plate_length",
      label: "Plate Length",
      value: 120,
      unit: "mm",
      description: "plate length",
      provenance: { source: "document", ref: "spec.pdf#p1:l2", quote: "REQ-1 Plate size 120 x 80 x 6 mm" },
    },
    {
      name: "mounting_hole_diameter",
      label: "Mounting Hole Diameter",
      value: 6.6,
      unit: "mm",
      description: "M6 clearance",
      provenance: { source: "standard", ref: "ISO 273" },
    },
  ],
  checks: [{ description: "Plate size 120 x 80 x 6 mm", passed: true, actual: "120 x 80 x 6" }],
  volume: 54893.96,
  build: () => ({ glb: asset("plate.glb"), thumbnail: asset("plate.png"), findings: [sensorFinding] }),
};

// Output of the geometry service for a 60 x 40 x 5 mm plate with a Ø10 hole at x = 20 (fails 1.5 x D) and x = 15 (passes).
const edgeBuilds: Record<number, Built> = {
  20: {
    glb: asset("edge-plate-x20.glb"),
    thumbnail: asset("edge-plate-x20.png"),
    findings: JSON.parse(asset("edge-plate-x20-findings.json").toString("utf8")) as Finding[],
  },
  15: { glb: asset("edge-plate-x15.glb"), thumbnail: asset("edge-plate-x15.png"), findings: [] },
};

export const edgePlate: Scenario = {
  title: "Edge test plate",
  prompt: "Plate 60 x 40 x 5 mm with a Ø10 hole 10 mm from the right edge",
  params: [
    {
      name: "hole_x",
      label: "Hole X",
      value: 20,
      unit: "mm",
      min: -25,
      max: 25,
      description: "hole centre x",
      provenance: { source: "prompt", quote: "a Ø10 hole 10 mm from the right edge" },
    },
  ],
  checks: [{ description: "Plate 60 x 40 x 5 mm", passed: true, actual: "60 x 40 x 5" }],
  volume: 11607.3,
  build: (values) => (values.hole_x === undefined ? undefined : edgeBuilds[values.hole_x]),
};

export const versionUrls = (number: number) => ({
  files: Object.fromEntries(
    (["step", "stl", "glb", "py", "ir"] as const).map((f) => [
      f,
      `/models/m1/export?fmt=${f}&version=${number}`,
    ]),
  ),
  thumbnail_url: `/models/m1/versions/${number}/thumbnail`,
});

export const firstVersion = (s: Scenario = sensorPlate): Version => ({
  model_id: "m1",
  number: 1,
  created: now(1),
  status: "ok",
  origin: "generate",
  prompt: s.prompt,
  params: s.params,
  checks: s.checks,
  findings: s.build(valuesOf(s.params))?.findings ?? [],
  metrics: { volume: s.volume, mass_g: null },
  ...versionUrls(1),
});

export const valuesOf = (params: Param[]) => Object.fromEntries(params.map((p) => [p.name, p.value]));

const fileNames = [
  "motor-mount-spec.pdf",
  "nema17-motor.step",
  "plate-design-rules.md",
  "notes.txt",
  "hole-table.csv",
  "sketch.png",
];

export const contextFiles: ContextFile[] = fileNames.map((name, i) => ({
  id: `f${i + 1}`,
  project_id: "p1",
  name,
  kind: name.split(".").pop() ?? "",
  role: "spec",
  status: "processed",
  facts: i + 1,
  rules: name.endsWith(".md") ? 2 : 0,
  uploaded: now(i),
  used_in: i === 0 ? ["m1"] : [],
}));

const relations = [
  { src: "f1", dst: "r1", type: "states" },
  { src: "f4", dst: "r1", type: "mentions" },
  { src: "m1", dst: "r1", type: "satisfies" },
  { src: "m1", dst: "f2", type: "similar_to" },
];

// Like the context service, deleting a file drops its entity and every relation touching it.
export const graphOf = (files: ContextFile[]): GraphView => {
  const nodes = [
    ...files.map((f) => ({ id: f.id, type: "file", name: f.name })),
    { id: "r1", type: "requirement", name: "REQ-1" },
    { id: "m1", type: "model", name: "Sensor plate" },
  ];
  const ids = new Set(nodes.map((n) => n.id));
  const edges = relations.filter((e) => ids.has(e.src) && ids.has(e.dst));
  return { nodes, edges, counts: { entities: nodes.length, relations: edges.length } };
};

export const graph = graphOf(contextFiles);
