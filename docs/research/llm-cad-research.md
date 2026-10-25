# LLM / ML for CAD: literature and assets

Researched 2026-10-25. Licences are marked "verified" where read from the dataset or repo page today. Everything else comes from the papers and memory and should be re-checked before use. "NC" means non-commercial.

## Key takeaways

1. **Code-as-CAD won.** Since 2025 the strongest open results emit CadQuery Python, not command-token sequences: CAD-Recode, cadrille, both CAD-Coders, Text-to-CadQuery, CAD-RL. Our IR → build123d design sits in this lineage, with a typed IR as the intermediate layer, which makes the output easier to validate and repair.
2. **Small Qwen models work when fine-tuned.** CAD-Recode is Qwen2-1.5B plus a point encoder. cadrille is Qwen2-VL-2B. CAD-Coder (text) is Qwen2.5-7B with SFT, then GRPO using a Chamfer-distance reward. This is direct evidence that 1.5B–7B Qwen models are viable for our IR emitter.
3. **Verify-and-repair loops help even without fine-tuning.** CADCodeVerify (render → VLM asks and answers questions about the render → fix the code) improves zero-shot output. That matches our planned vision-critique and repair loop.
4. **Almost all large datasets are NC.** Fusion 360 Gallery, Text2CAD, CAD-Recode and Point2CAD code are all NC. The DeepCAD/ABC-derived data comes from Onshape public documents, so commercial status is unclear. For **weights we redistribute under Apache-2.0**, train on (a) our own procedurally generated IR corpus (CAD-Recode showed procedural data generalises), (b) permissively licensed sets (CAD-Coder-text dataset, Apache-2.0 per its HF metadata), and use the NC sets only for evaluation.
5. **Mesh/point cloud → parametric reconstruction is still research grade.** Point2CAD and ComplexGen recover B-rep surfaces and topology, not editable features. CAD-Recode and cadrille recover simple sketch-extrude programs. Backflip (commercial) is the only polished product. We should start with primitive fitting plus an LLM-proposed IR, scored by Chamfer/IoU against the mesh.

## Table

| Paper | Year / venue | Input → output | Code? | Weights? | Dataset & licence | Usable for fine-tuning our IR? |
|---|---|---|---|---|---|---|
| [DeepCAD](https://github.com/ChrisWu1997/DeepCAD) (Wu et al.) | 2021 ICCV | latent/random → sketch+extrude command sequence | yes (MIT) | yes | 178k models from ABC/Onshape; data from public Onshape docs, so commercial status unclear | **Yes, as structure.** Sketch-extrude JSON maps almost 1:1 to IR. Convert, then use for eval or internal SFT |
| [Fusion 360 Gallery](https://github.com/AutodeskAILab/Fusion360GalleryDataset) (Willis et al.) + JoinABLe | 2021 SIGGRAPH; 2022 CVPR | reconstruction sequences; assemblies and joints | yes | baselines | 8.6k reconstruction sequences, 8.2k assemblies, 32k joints. **Non-commercial research only, no redistribution** (verified, LICENSE.md) | Eval and research only. The joint data is the best public mate/joint supervision |
| SketchGraphs (Seff et al.) | 2020 ICML-W | constraint-graph sketches | yes (MIT) | yes | 15M Onshape sketches with constraints; Onshape-derived | Good for sketch-constraint priors (eval/research) |
| [Text2CAD](https://huggingface.co/datasets/SadilKhan/Text2CAD) (Khan et al.) | 2024 NeurIPS | text (4 skill levels) → DeepCAD sequence | yes | yes (`Text2CAD_1.0.pth`) | ~170k DeepCAD models × 4 prompt levels; **CC BY-NC-SA 4.0** (verified); 605 GB with renders, but the CSV is 1.3 GB | Prompts are very useful for eval. NC-SA blocks redistributed weights |
| [CAD-Recode](https://github.com/filaPro/cad-recode) (Rukhovich et al.) | 2025 ICCV | point cloud → CadQuery Python (Qwen2-1.5B) | yes | yes: `filapro/cad-recode`, `-v1.5` | 1M procedurally generated CadQuery scripts, 378 MB, **CC BY-NC 4.0** (verified) | Method yes: copy the procedural-generator idea. Data is NC |
| [cadrille](https://github.com/col14m/cadrille) (Kolodiazhnyi et al.) | 2025 arXiv 2505.22914 | point cloud / image / text → CadQuery (Qwen2-VL-2B, SFT + RL) | yes (Apache-2.0, verified) | yes: `maksimko123/cadrille`, `-rl` | Trained on CAD-Recode and Text2CAD (both NC) | Best open multimodal baseline to benchmark against. Weights inherit NC-data questions |
| [CAD-Coder (text)](https://arxiv.org/abs/2505.19713) (Guan et al.) | 2025 NeurIPS | text → CoT → CadQuery; SFT then GRPO (Chamfer + format reward) | yes | partial (not verified) | [`gudo7208/CAD-Coder`](https://huggingface.co/datasets/gudo7208/CAD-Coder), Apache-2.0 per HF metadata | **Yes.** The most permissive text→CadQuery set; convert to IR. The GRPO recipe applies later |
| [CAD-Coder (image)](https://arxiv.org/abs/2505.14646) (Doris et al., MIT) | 2025 arXiv; 2026 JMD | image → CadQuery (LLaVA-1.5 / Vicuna-13B) | yes (Apache-2.0 per mirror, not verified) | yes (13B, too large for us) | GenCAD-Code, 163k image–code pairs (licence not stated) | Image→code pairs are useful for VLM eval |
| [CADCodeVerify / CADPrompt](https://arxiv.org/abs/2410.05340) (Alrashedy et al.) | 2025 ICLR | text → CadQuery with VLM render-question-refine loop | not found | n/a (uses API VLMs) | CADPrompt: 200 prompts with expert code | **Adopt CADPrompt as a smoke-eval set** (if the licence allows) and the verify loop design |
| Text-to-CadQuery (Xie & Ju) | 2025 arXiv 2505.06507 | text → CadQuery; fine-tunes 124M–7B | yes | some | ~170k CadQuery annotations on Text2CAD/DeepCAD (inherits NC) | Eval / internal |
| [CAD-RL / ExeCAD](https://arxiv.org/abs/2508.10118) | 2025 arXiv | multimodal CoT + RL → CadQuery | partial | ? | ExeCAD 16.5k real-world description/CadQuery/render triples | Eval; check licence |
| CADFusion (Wang et al., Microsoft) | 2025 ICML | text → CAD sequence with visual-feedback alternation | yes | yes (8B) | DeepCAD-derived | Method reference (visual feedback) |
| CAD-Llama (Li et al.) | 2025 CVPR | text → hierarchical "SPCC" code | partial | ? | DeepCAD-derived | Method reference |
| FlexCAD (Zhang et al.) | 2025 ICLR | masked/controllable CAD editing via LLM | yes | yes | DeepCAD-derived | Reference for **edit** tasks (change one feature) |
| CAD-MLLM / Omni-CAD (Xu et al.) | 2024 arXiv | text / image / point → command sequence | partial | ? | Omni-CAD 450k | Reference |
| [GenCAD](https://arxiv.org/abs/2409.16294) (Alam & Ahmed) | 2024 arXiv; TMLR 2025 | image → command sequence (contrastive + diffusion prior) | yes | yes | DeepCAD-derived | Low; superseded by code-gen |
| Img2CAD (Chen et al.) | 2024 arXiv 2408.01437 | image → CAD via VLM structure + param regressor | partial | ? | own (ShapeNet-like) | Reference for the "VLM decides structure, regressor decides numbers" split |
| OpenECAD (Yuan et al.) | 2024 arXiv | image → CAD code (TinyLLaVA 0.55–3.1B) | yes | yes (small) | own synthetic | Small-VLM reference |
| Sketch2CAD / Free2CAD (Li et al.) | 2020 / 2022 SIGGRAPH (Asia) | freehand strokes → sketch-extrude ops | yes (Free2CAD) | yes | synthetic | Reference for sketch interpretation |
| [Point2CAD](https://github.com/prs-eth/point2cad) (Liu et al.) | 2024 CVPR | segmented point cloud → B-rep surfaces, edges, corners (non-parametric) | yes, **CC BY-NC 4.0** per README (sidebar says Apache; inconsistent, verified) | ParseNet segmentation weights | ABC | No (not parametric). Reference for mesh→B-rep |
| ComplexGen (Guo et al.) | 2022 SIGGRAPH | point cloud → B-rep chain complex | yes (licence not checked) | yes | ABC | No (not parametric) |
| [BrepGen](https://github.com/samxuxiang/BrepGen) (Xu et al., Autodesk) | 2024 SIGGRAPH | unconditional / class → B-rep (diffusion) | yes | yes | DeepCAD/ABC | No (not text/parametric) |
| [BenchCAD](https://arxiv.org/abs/2605.10865) | 2026 arXiv | benchmark: image→code, code QA, instruction editing | ? | — | 17.9k execution-verified CadQuery programs, 106 industrial part families | **Eval** (industrial realism); check licence |
| [Text2CAD-Bench](https://arxiv.org/abs/2605.18430) | 2026 arXiv | benchmark: text → parametric CadQuery, 4 difficulty levels | ? | — | human-in-the-loop CadQuery | **Eval** |

## Recommended data plan for our IR emitter

1. **Eval first:** a fixed suite of about 50 CADPrompt-style prompts, a slice of Text2CAD-Bench/BenchCAD, and our own spec-driven cases. Metrics: IR schema-valid %, compile %, B-rep valid %, IoU/Chamfer against reference, and parameter error.
2. **Licence-clean SFT corpus:** a procedural IR sampler (plates, brackets, flanges, enclosures, shafts with standard holes from `bd_warehouse` tables) → compile → render → local Qwen writes 2–4 descriptions per sample at different expertise levels (the Text2CAD idea). Add converted CAD-Coder-text samples (Apache-2.0).
3. **Later:** GRPO/RL with a geometric reward (CAD-Coder recipe), using the compiler as the verifier. That is out of reach on 6 GB except for ≤1.5B models.

Sources: linked inline; dataset licences checked on the HF/GitHub pages on 2026-10-25.
