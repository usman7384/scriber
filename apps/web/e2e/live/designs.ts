import { repoFile } from "./live";

// IR posted to POST /projects/{id}/designs: the same parts the mocked suite's fixtures were built from (make_fixtures.py, test_dfm.plate).
export const basePlate = JSON.parse(repoFile("evals/parity/m3/base_plate.json").toString()) as object;

export const edgePlate = (holeX: number) => ({
  title: "Edge test plate",
  params: [{ name: "hole_x", value: holeX, unit: "mm", min: 0, max: 25 }],
  parts: [
    {
      id: "p",
      name: "Plate",
      sketches: [{ id: "s", entities: [{ kind: "rect", width: 60, height: 40 }] }],
      features: [
        { kind: "extrude", id: "body", name: "Plate", sketch: "s", distance: 5 },
        {
          kind: "hole",
          id: "h",
          name: "Hole",
          plane: { offset: 5 },
          at: { kind: "points", points: [["hole_x", 0]] },
          diameter: 10,
        },
      ],
    },
  ],
});

const block = (id: string, size: number) => ({
  id,
  name: id[0]?.toUpperCase() + id.slice(1),
  material: "PLA",
  sketches: [{ id: "s", entities: [{ kind: "rect", width: size, height: size }] }],
  features: [{ kind: "extrude", id: "body", name: "Body", sketch: "s", distance: size }],
});

export const stack = {
  title: "Stack",
  params: [],
  parts: [block("plate", 40), block("cube", 10)],
  assembly: {
    connectors: [
      { id: "seat", part: "plate", origin: [0, 0, 40] },
      { id: "foot", part: "cube" },
    ],
    joints: [{ id: "cube_on_plate", parent: "seat", child: "foot" }],
  },
};
