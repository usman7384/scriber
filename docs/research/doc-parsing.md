# Document parsing: specs, tables, dimensions and design rules

Researched 2026-10-25. Versions are the latest on PyPI as resolved by `uv pip compile` today (verified). Licences come from PyPI metadata.

## TL;DR

- **Default (light, permissive): `pypdfium2` + `pdfplumber` + `camelot-py`**. Text with coordinates, words and lines, and tables (lattice and stream). Total install is tens of MB, with no torch. Windows wheels exist for all three.
- **Optional extra `[docs-ml]`: `docling` 2.142.1 (MIT)** for scanned or complex-layout PDFs (layout model, TableFormer, OCR). It pulls in torch (CPU) and roughly 0.5 GB of models, so it is lazy-loaded and off by default.
- **Do not depend on PyMuPDF (AGPL-3.0).** It is the best performer, but it would force AGPL obligations on an Apache-2.0 distribution. Same for **marker** 2.0.0: the code is now Apache-2.0, but its model weights use a modified Open RAIL-M licence with a revenue/funding cap.
- DOCX: `python-docx` 1.2.0 (MIT), which handles paragraphs, tables and styles. Spreadsheets: `pandas` 3.1 + `openpyxl` 3.1.5.
- Units: **`pint` 0.25.3** (BSD-3). Verified on Windows: mm↔inch conversion and quantity arithmetic.

## Parser comparison

| Library | Version | Licence | Install weight | Windows | Text + coords | Tables | Scanned/OCR | Notes |
|---|---|---|---|---|---|---|---|---|
| **pypdfium2** | 5.14.0 | Apache-2.0 / BSD-3 | ~5 MB wheel | yes | yes (fast) | no | no (renders pages for OCR/VLM) | Google PDFium. Also our page rasteriser for the VLM |
| **pdfplumber** | 0.11.10 | MIT | small (pdfminer.six) | yes | yes (chars, words, lines, rects) | heuristic `extract_tables` | no | Best for bbox-level provenance of dimensions |
| **camelot-py** | 2.0.0 | MIT | moderate (opencv-headless) | yes | — | **lattice** (ruled) + **stream** | no | Good on datasheet tables; recent versions use a pdfium backend instead of Ghostscript (re-check on install) |
| **docling** | 2.142.1 | MIT (models `docling-ibm-models` MIT) | heavy: torch CPU + layout/TableFormer models | yes | yes (layout-aware, reading order) | **best open** (TableFormer) | yes (EasyOCR/RapidOCR/Tesseract plug-ins) | Exports Markdown/JSON with page and bbox provenance. The optional ML path |
| unstructured | 0.27.34 | Apache-2.0 | heavy with `[pdf]` hi_res (detectron/yolox, poppler, tesseract) | partial (system deps) | element-level | via hi_res | yes | More ETL framework than we need |
| marker-pdf | 2.0.0 | code Apache-2.0; **weights Open RAIL-M variant, commercial cap** | heavy (torch + surya) | yes | Markdown | yes | yes | Licence risk; skip |
| PyMuPDF | 2.0 | **AGPL-3.0** or commercial | ~20 MB | yes | excellent | `find_tables` | via Tesseract | **Excluded** (AGPL conflict) |
| python-docx | 1.2.0 | MIT | small | yes | paragraphs/runs | `doc.tables` | n/a | DOCX specs |
| pint | 0.25.3 | BSD-3 | small | yes | — | — | — | Unit parsing and normalisation (**verified**) |

## Pipeline

```
file → sniff type
  PDF  → pypdfium2 text? ── yes → pdfplumber words+bbox, camelot tables
                         └─ no (scanned) → [docling OCR] or rasterise → VLM transcription
  DOCX → python-docx paragraphs + tables
  CSV/XLSX → pandas
→ Chunk(doc_id, page, bbox, section_path, text | table_json)
→ extractors:
   1. regex/grammar dimension tagger (deterministic)
   2. LLM rule extractor (schema-constrained, local Qwen)
→ KG upsert (knowledge-graph.md) + vector index
```

### Deterministic dimension and tolerance tagger

Regex/PEG rules run before any LLM, so numbers are never hallucinated. The LLM only links them.

| Pattern | Example | Normalised |
|---|---|---|
| value + unit | `6 mm`, `0.25"`, `25,4 mm` | `Quantity(6,'mm')` (decimal comma handled) |
| diameter / radius | `Ø6`, `⌀6`, `dia. 6`, `R2` | `{kind: diameter, value: 6 mm}` |
| metric thread | `M6x1`, `M6×1.0-6H` | `{thread: M6, pitch: 1 mm, class: 6H}` → ISO 261/262 table |
| symmetric tolerance | `20 ±0.1` | `{nominal: 20, upper: +0.1, lower: −0.1}` |
| asymmetric tolerance | `20 +0.05/-0`, `20 +0.05 -0.02` | upper/lower |
| ISO 286 fit | `Ø10 H7`, `10 g6` | computed limits (IT grade and fundamental deviation tables; implement ISO 286-1 formulas) |
| angle | `45°`, `1.5 deg` | `Quantity(45,'deg')` |
| roughness | `Ra 1.6` | `{Ra: 1.6 µm}` |
| ranges / limits | `≥ 2 mm`, `min. 2 mm`, `max 0.5` | comparator + value |

Every tag keeps `(doc_id, page, bbox, char_span)` as **provenance**. IR parameters cite this.

### Design rules → machine-checkable constraints

Approach: the LLM proposes rules into a **strict schema**. The UI shows each rule next to its source span for one-click accept or edit. Only accepted rules are enforced. Rules evaluate against IR parameters (pre-compile) or B-rep metrics from the DFM module (post-compile).

```jsonc
// DesignRule (Pydantic → JSON schema → Ollama `format`)
{
  "id": "R-0012",
  "statement": "Minimum wall thickness for PA12 SLS parts is 0.8 mm",   // verbatim or near
  "source": {"doc_id": "D3", "page": 4, "bbox": [72,310,520,330], "quote": "…"},
  "scope": {                                   // which entities the rule applies to
    "process": ["sls"], "material": ["PA12"], "part_tags": [], "feature_types": []
  },
  "metric": "min_wall_thickness",              // enum from the DFM metric registry
  "comparator": ">=",                          // enum: >=, <=, ==, in_range, one_of
  "value": {"magnitude": 0.8, "unit": "mm"},  // pint-parsable
  "value_max": null,
  "severity": "error",                          // error | warning | info
  "standard_ref": null,                         // e.g. "ISO 2768-m", "DIN 912"
  "confidence": 0.82,
  "status": "proposed"                          // proposed | accepted | rejected | edited
}
```

- The `metric` enum is the contract between the extractor and the checker. Start with `min_wall_thickness`, `hole_edge_distance`, `min_hole_diameter`, `hole_depth_to_diameter`, `min_internal_radius`, `draft_angle`, `max_overhang_angle`, `min_feature_size`, `max_part_envelope`, `thread_engagement_min`, `material_allowed`, `fastener_standard_allowed`, and `tolerance_general` (ISO 2768 class).
- Rules that do not map to a metric are stored as `metric: "unstructured"`. They are retrieved into prompts as guidance but not auto-checked.
- Extraction prompt: one chunk at a time, few-shot, schema-constrained, `temperature: 0`. Then a deterministic cross-check: the extracted value **must** appear among the tagger's quantities for that chunk, or the rule is flagged `low_confidence`.

## Risks

- Datasheet tables with merged cells or rotated headers: camelot lattice handles ruled tables. Fall back to docling, or to "render page → VLM → table JSON" (slow but local).
- Scanned PDFs without the ML extra: text is unavailable. Tell the user, and offer the docling extra or VLM transcription page by page (about 10–20 s per page on the 4B model; estimate).
- Standards documents (ISO/DIN) are copyrighted. Users may ingest their own copies. We must not ship their text, only factual numeric tables we derive or that are openly licensed (see `dfm-and-standards.md`).

Sources: PyPI metadata for each package (2026-10-25); [marker licence note on PyPI](https://pypi.org/project/marker-pdf/); [PyMuPDF licence](https://pypi.org/project/PyMuPDF/); [docling](https://github.com/docling-project/docling).
