# M4 parity: vision rows

Demos for IN-4, IN-5, IN-6 and VM-10 in `evals/src/scriber_evals/parity_m4_vision.py` (`ROWS`). Requirement extraction runs on `rig.llm`; every call that carries an image goes to the configured vision model (`llm.vision` in `config.yaml`, `qwen3.5:4b`), built with `llm_for`.

## Run

```bash
uv run python evals/parity/m4/vision/make_fixtures.py   # regenerates the images, the drawing PDF and critic_cases.json
uv run pytest evals/tests/test_parity_m4_vision.py      # offline, FakeLLM, about 25 s
uv run scriber-parity IN-4 IN-5 IN-6 VM-10            # live, once the integrator registers parity_m4_vision.ROWS
```

## Product changes

- `generate(..., vision=)` and `refine(..., vision=)`: when images are attached and a vision model is given, the design call and its repairs go to it (with its own few-shot setting); requirement extraction stays on the text model. Without images nothing changes.
- With images, the design message gets `IMAGE_NOTE`: take shape and dimensions from the image, cite read values as provenance `vision`, text wins where they differ. Text-only prompts are byte-identical to before.
- `critique(request, views, llm) -> Critique(findings, matches)`: one schema-constrained call to the vision model. It is an explicit call, not part of the generate loop.
- `LLMConfig.vision` (default `qwen3.5:4b`).

## Fixtures (`evals/parity/m4/vision/`, all made by `make_fixtures.py`)

- `l_bracket_sketch.png`: a pencil-style oblique sketch of an L-bracket labelled 120, 40, 4 and 2x Ø6; the upright leg is drawn but not dimensioned.
- `servo.png`: a flat-shaded drawing of a servo-like box with mounting tabs, holes, shaft and cable. Our own illustration, not a photo; `servo_datasheet.md` holds generic 9 g micro-servo dimensions.
- `flange_drawing.pdf`: a vector drawing (front view and section) with text dimensions Ø120, PCD Ø90, 6× Ø11, hub Ø60, bore Ø30, 12 and 32. The demo sends both the PDF text (`document_text`) and the page rendered at 2x (pypdfium2).
- `critic_cases.json`: five parts with their requests (corner-hole plate, bolt-circle flange, bar with three holes, L-bracket, NEMA 17 plate). The wrong variant drops the last point of the hole feature.

## Rows

| Row | Demo measures | Offline | Live run needs |
|---|---|---|---|
| IN-4 | params whose name contains `length`/`width`/`thick` within 2 % of 120/40/4; 2 holes in the built part | pass | the vision model must read the sketch labels |
| IN-5 | sorted bbox within 10 % of the datasheet 32.2 × 11.8 × 26.7; ≥ 5 params; tab hole spacing reported for DP-12 | pass | the model must build body, tabs and shaft into one solid |
| IN-6 | the param nearest each of 120/90/11/60 within 0.1; built: 6 holes Ø11 ±0.1 at radius 45 ±0.1, OD 120 ±0.1 | pass | the model must turn the drawing into a flange with a hub |
| VM-10 | iso and plan views (512 px) of right and wrong parts; wrong flagged ≥ 4/5 and right flagged ≤ 1/5 | pass | qwen3.5:4b must count holes in the views |

VM-10 adds a control the checklist does not state: the correct parts must mostly pass, since a critic that rejects everything would otherwise meet the row.

## Gaps

- The API does not route images to the vision model yet: `work.py` must pass `vision=` to `generate`/`refine` (an `llm_for(config, config.llm.vision)` held next to `d.llm`). Until then IN-16/IN-17 image jobs go to the text-only default.
- The API does not rasterise PDF drawings; the demo does it with pypdfium2, which evals use without declaring it (it comes with `scriber-context`).
- The thumbnail renderer has one fixed camera. The plan view is made by turning the mesh onto that camera in the demo; named views belong in geometry.
- `AnthropicLLM` drops images, so hosted reference runs cannot do these rows.
- Not run live: the GPU was busy, so every number above is from scripted answers.
