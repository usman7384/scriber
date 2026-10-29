# Apps on the API

Small scripts in `examples/` that build parts through the HTTP API (`docs/API.md`) without the model: they compute a design in our IR and post it to `POST /projects/{id}/designs`, then wait for the job and download the result. Start the API with `uv run partwright serve` and create a project first (`POST /projects`).

## Shadow-box insert from a tool STL (`examples/shadow_box.py`)

```bash
uv run python examples/shadow_box.py spanner.stl --project <id> --offset 1.0 --out insert.step
```

- Reads the tool STL with trimesh and takes the outer loop of the section at half height as the tool outline, so it suits tools that lie flat (constant outline along Z). A tool whose silhouette changes with height needs a polygon union of its projection, which is not built.
- Offsets the outline outward by `offset`: straight walls move out along their normal, concave corners meet at the miter point and convex corners get an arc of radius `offset`, so every wall point is `offset` from the tool. The path points are expressions in the `offset` parameter, so `PATCH /models/{id}/params {"values": {"offset": 1.5}}` regrows the pocket.
- The insert is a block `margin` larger than the tool on every side, with the pocket `pocket_depth` (the tool thickness) deep over a `floor`.
- Measured on the parity spanner (AP-6): every sampled pocket wall point is 1.000 mm from the tool outline (see `docs/agents/parity-m5-platform.md`).

## Phone holder from the phone width (`examples/phone_holder.py`)

```bash
uv run python examples/phone_holder.py 75 --project <id> --out holder.stl
```

A U-shaped cradle extruded along Y whose inner width is the expression `phone_width + clearance` (clearance 0.5 mm total by default). `phone_width` carries the input as its provenance. Measured on a 75 mm phone (DP-19): inner width 75.5 mm.

## Sizing XML with no manual step (`partwright pipe`)

```bash
cat sizing.xml | uv run partwright pipe --project <id> --out wing.step
```

Posts the XML to `POST /projects/{id}/sizing` (the D-031 adapter turns it into IR on the server), waits for the job and saves the STEP. Without `--project` it creates a project named `pipe`.
