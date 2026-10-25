# Sketches and photos → IR with local models

Researched 2026-10-25. No VLM was run on sketches in this session (disk and VRAM were shared with other work). The capability statements below come from published benchmarks and model cards and should be measured in M1 on a 20-sketch eval set.

## What a local 4B VLM can and cannot do (Qwen3.5-4B / Qwen3-VL-4B at Q4)

| Task | Expectation | Evidence |
|---|---|---|
| Classify part type and list features (plate with 4 holes, L-bracket, flange, shaft with keyway) | **good** | General VLM ability; CAD-Coder (image) and cadrille show image → CadQuery is learnable even at 2B after fine-tuning |
| Read **printed/CAD** dimension text on clean drawings | **good** on crops, fair on full pages | Title-block extraction with Qwen2.5-VL works ([EC3 2026](https://ec-3.org/publication/ec32026_252/)); MechVQA has a dimension category |
| Read **handwritten** numbers | fair. Better when the region is cropped and the model is asked about a single value | Not measured; typical VLM OCR behaviour |
| Associate a dimension with a feature/edge ("this 40 is the overall width") | **weak–fair**, the main failure mode | Enginuity (Jun 2026): models locate components but do poorly on fidelity and free-form reasoning ([arXiv 2606.03410](https://arxiv.org/abs/2606.03410)) |
| Interpret orthographic views (front/top/side → 3D) | fair for prismatic parts; poor for complex parts | — |
| Precise coordinates and geometry from pixels | **poor**, so do not rely on the VLM for numbers it cannot read | — |
| Photo of a real part → dimensions | impossible without a scale reference; with an ArUco marker or ruler, ±1–2 mm on planar features | classical CV |

Conclusion: **the VLM decides structure, while OCR and CV supply the numbers and positions.** The user confirms anything unresolved. This is the same split as Img2CAD (VLM for structure, regressor for parameters).

## Classical helpers

| Tool | Version | Licence | Use |
|---|---|---|---|
| `opencv-python-headless` | 5.0.0.93 | Apache-2.0 | Adaptive threshold and deskew, `Canny`, `HoughLinesP`/LSD for lines, `HoughCircles` for holes, `findContours` + `approxPolyDP` for profiles, dimension-arrow detection (template matching), ArUco markers (main module) for photo scale and perspective |
| **RapidOCR** | 3.10.0 | Apache-2.0 | **Default OCR.** PP-OCR models on onnxruntime: small (tens of MB), CPU-fast, Windows wheels, returns text boxes |
| PaddleOCR | 3.7.0 | Apache-2.0 | Better accuracy, but `paddlepaddle` is hundreds of MB. Optional |
| Tesseract (`pytesseract` 0.3.13) | 5.x | Apache-2.0 | Needs a separate Windows binary (UB Mannheim). Weak on handwriting. Not default |
| TrOCR-handwritten (HF) | — | MIT | Optional handwriting reader for crops (~334M params, CPU OK) |

## Pipeline

```
image ─► preprocess (EXIF rotate, deskew, CLAHE, ≤1024 px long side)
   ├─► CV:  lines, circles, closed contours → candidate profile polylines (px) + dimension-line/arrow candidates
   ├─► OCR: RapidOCR boxes → parse with the dimension tagger (Ø, R, M6, ±, H7 …) → numeric candidates (px bbox)
   └─► VLM pass 1 (qwen3.5:4b, format = SketchInterpretation schema, think:false):
          views, part_class, features[], dimension *intent* ("overall width", "hole Ø") with approximate bboxes
   ─► VLM pass 2 (per uncertain number): crop around the OCR box → "what exactly is written?" → reconcile with OCR
   ─► Fusion (deterministic):
          attach each numeric candidate to the nearest dimension line/feature (bbox geometry + VLM intent)
          solve px→mm scale by least squares over attached linear dims; flag dims whose residual is > 5 %
          snap CV geometry to dims (holes → circles, overall box → outer contour)
   ─► SketchInterpretation JSON (below) → IR emitter (LLM, text-only) → IR with unresolved params marked
   ─► UI: overlay detected dims on the image; the user confirms or edits any with confidence < 0.7
```

### SketchInterpretation (schema sketch)

```jsonc
{
  "views": [{"id": "V1", "kind": "front|top|side|iso|section|unknown", "bbox": [x0,y0,x1,y1]}],
  "part_class": "plate|bracket|flange|shaft|enclosure|other",
  "features": [{"id": "F1", "type": "outline|hole|slot|pocket|boss|fillet|chamfer|thread|pattern",
                "view": "V1", "bbox": [..], "count": 4, "pattern": {"kind": "rect", "pitch_hint": null}}],
  "dimensions": [{"id": "D1", "text": "Ø6 H7", "kind": "linear|diameter|radius|angle|thread",
                  "value": 6, "unit": "mm", "tolerance": {"fit": "H7"},
                  "attaches_to": {"feature": "F1", "measure": "diameter"},
                  "bbox": [..], "source": "ocr|vlm|both", "confidence": 0.86}],
  "scale_mm_per_px": 0.212, "scale_residual": 0.03,
  "assumptions": ["thickness not given; default 5 mm from project rule R-0003"],
  "questions":   ["Is the 40 mm the overall width including the flanges?"]
}
```

- Unit default: mm unless an inch mark or a project setting says otherwise. Every value carries `source` and `confidence` into IR provenance (`kind: "sketch"`, image id, bbox).
- Missing dimensions are never invented silently. They come from a project rule or default (cited), or they become a **question**.

## Meshes and photos of physical parts (related input)

- STL/OBJ: `trimesh` 5.2 for repair and units, then primitive fitting (RANSAC planes/cylinders), then the LLM proposes an IR, then compile, then score Chamfer/IoU against the mesh. Iterate with the repair loop (see `llm-cad-research.md`; Point2CAD/ComplexGen are not parametric).
- Photos: require a scale reference (ArUco, or a card of known size) and treat the output as approximate. The UI must show "estimated".

## Fine-tuning path (later)

Collect user-confirmed `(image, SketchInterpretation)` pairs, plus synthetic renders of our procedural IR corpus with OpenCV "hand-drawn" augmentation (wobble, line jitter, handwriting fonts). A LoRA on the Qwen3.5-0.8B/2B vision path is a candidate, but VRAM is tight (see `fine-tuning.md`).
