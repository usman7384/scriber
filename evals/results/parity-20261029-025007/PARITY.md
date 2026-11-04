Model: `scriber-ir:4b-s1`

| row | result | measured | note |
|---|---|---|---|
| PR-2 | pass | label=Base Bolt Spacing X, spacing=90.0, llm_calls=0, edits=5, rebuild_p50_ms=234, rebuild_max_ms=296, job_wall_p50_ms=719 | rebuild = kernel build and export; job wall adds thumbnail, shape descriptor and graph record |
| PR-9 | pass | versions=4, with_prompt=4, png_256=4, restored_as=5, params_equal_v1=True |  |
| EX-7 | pass | deliveries=3, keys=files, model_id, version, version=1, step_bytes=31652 |  |
| AP-1 | pass | anonymous=401, bearer=200, x_api_token=200, before_revoke=200, revoke=204, after_revoke=401 |  |
| AP-4 | pass | job=done, boss_x=30.0, foreign_param=400, params_changed=boss_d, base_metrics_same=True, base_ir_same=True |  |
| AP-5 | pass | step_schema=AP214, step_solids=1, volume_drift=7.275957614183426e-12, stl_watertight=True, chordal_deviation_mm=0.00103, gltf_errors=0, mesh_nodes=Plate |  |
| CD-2 | pass | versions=4, param_change=[{"name": "base_bolt_spacing_x", "old": 85.0, "new": 90.0}], features_added=plate.fillet, sources=params: base_bolt_spacing_x=90, refine: round the vertical edges with 1 mm fillets, restore: Base plate 120 x 80 x 5 mm with four 6.6 mm bolt holes | seeded designs |
| WP-7 | pass | submitted=queued, observed_running=True, done=done, failed=failed, error=gave up after 6 attempts, log_job_id=jef39c18ba9e0, log_request_id=ra0f4222c6d12 |  |
| PF-4 | pass | label=Base Bolt Spacing X, spacing=90.0, llm_calls=0, edits=10, rebuild_p50_ms=264.5, rebuild_max_ms=531, job_wall_p50_ms=703 | rebuild = kernel build and export; job wall adds thumbnail, shape descriptor and graph record |
| PR-7 | FAIL |  | ConnectionError: Failed to connect to Ollama. Please check that Ollama is downloaded, running and accessible. https://ollama.com/download |
| PR-10 | pass | L=120.0, W=80.0, H=5.0, step_sorted=5, 80, 120 | API half (version metrics); the on-model labels are the web suite's |
| EX-6 | pass | view=200, glb_magic=glTF, write=401, revoke=204, after_revoke=404 | API half; the read-only viewer page is the web suite's |
| WP-6 | FAIL | step_events=0, progress=, final=failed | API half; the bar is the web suite's |
| CX-1 | pass | uploaded=6, listed=6, processed=6, progress=0/100 0/100 0/100 0/100 0/100 0/100, kinds=pdf, md, txt, csv, image, step | API half; per-file progress bars are the web suite's |
| CX-3 | FAIL | job=failed, recorded=, selected=fef47d7f497a0, f8afe5740b9d1, used_in={"fef47d7f497a0": [], "f8afe5740b9d1": [], "f3d5dcec6acf1": []} | API half; the 'Used in' column is the web suite's |
| CX-6 | pass | files=3, facts=15, rules=0, generations=2, used_in_generation=3, score=120, level=1, next_level_score=400 | formula in docs/agents/context.md; UI half is web's |

13/16 rows pass
