#!/usr/bin/env bash
# after s2.sh: import the S2 GGUF and run the gates for S2 and the current default in one session (D-028)
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
export PYTHONIOENCODING=utf-8
until grep -q "^done" data/training/s2/pipeline.log; do grep -q "^exit [1-9]" data/training/s2/pipeline.log && { echo "pipeline failed"; exit 1; }; sleep 30; done
(cd training/wsl && ollama create partwright-ir:4b-s2 -f Modelfile.4b-s2) || exit 1
date
uv run partwright-evals evals/cases/dev.yaml --models partwright-ir:4b-s2 partwright-ir:4b-s1 | tail -6
uv run partwright-evals evals/cases/m1.yaml --models partwright-ir:4b-s2 partwright-ir:4b-s1 | tail -6
for m in partwright-ir:4b-s2 partwright-ir:4b-s1; do uv run partwright-grounded --model $m | tail -8; done
date
