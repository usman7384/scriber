import type { ContextFile, GraphView, Param, Version } from "../src/api";

export const now = (minute: number) => `2026-10-26T10:${String(minute).padStart(2, "0")}:00Z`;

export const project = {
  id: "p1",
  name: "Bracket lab",
  created: now(0),
  model_count: 0,
  file_count: 6,
};

export const params: Param[] = [
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
];

export const firstVersion = (): Version => ({
  model_id: "m1",
  number: 1,
  created: now(1),
  status: "ok",
  origin: "generate",
  prompt: "Sensor plate 120 x 80 x 6 mm with four M6 holes",
  params,
  checks: [{ description: "Plate size 120 x 80 x 6 mm", passed: true, actual: "120 x 80 x 6" }],
  findings: [
    {
      rule_id: "min_hole_edge_ratio",
      severity: "warning",
      binding: "static",
      message: "Hole Ø6.6 is 10 mm from the edge; needs at least 13.2 mm",
      location: { point: [26.85, 16.85, 6], face: null },
      suggestion: "Keep hole centres within x ±46.8 and y ±26.8",
    },
  ],
  metrics: { volume: 54893.96, mass_g: null },
  files: {
    step: "/models/m1/export?fmt=step&version=1",
    stl: "/models/m1/export?fmt=stl&version=1",
    glb: "/models/m1/export?fmt=glb&version=1",
    py: "/models/m1/export?fmt=py&version=1",
    ir: "/models/m1/export?fmt=ir&version=1",
  },
  thumbnail_url: "/models/m1/thumbnail.svg",
});

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

export const graph: GraphView = {
  nodes: [
    ...contextFiles.map((f) => ({ id: f.id, type: "file", name: f.name })),
    { id: "r1", type: "requirement", name: "REQ-1" },
    { id: "m1", type: "model", name: "Sensor plate" },
  ],
  edges: [
    { src: "f1", dst: "r1", type: "states" },
    { src: "m1", dst: "r1", type: "satisfies" },
    { src: "m1", dst: "f2", type: "similar_to" },
  ],
  counts: { entities: 8, relations: 3 },
};

export const thumbnail =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 30"><rect x="5" y="8" width="30" height="14" fill="#9aa7b4"/></svg>';
