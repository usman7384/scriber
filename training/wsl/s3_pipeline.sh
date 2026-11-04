#!/usr/bin/env bash
# S3 end to end on this laptop: S2 showcase baseline, on-policy collection, dataset, WSL training and export, import, gates (D-028)
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
export PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1
out=data/training/s3
mkdir -p "$out"
step() { echo "$1 $(date)"; }
step baseline; uv run scriber-parity M6-SHOWCASE --model scriber-ir:4b-s2 > "$out/showcase-s2.log" 2>&1
step collect; uv run scriber-collect --s3 --model scriber-ir:4b-s2 --specs 200 --seed 3 --out "$out/onpolicy-4b-s2.jsonl" > "$out/collect-4b-s2.log" 2>&1
uv run scriber-collect --s3 --model qwen3.5:4b --specs 200 --seed 3 --out "$out/onpolicy-qwen3.5-4b.jsonl" > "$out/collect-qwen3.5-4b.log" 2>&1
step dataset; uv run scriber-dataset --s3 --seed 3 --specs 2900 --workers 4 --paraphrase-model qwen3.5:4b --onpolicy "$out/onpolicy-4b-s2.jsonl" "$out/onpolicy-qwen3.5-4b.jsonl" --out "$out" > "$out/dataset.log" 2>&1 || { step "dataset-failed"; exit 1; }
ollama stop qwen3.5:4b >/dev/null 2>&1; ollama stop scriber-ir:4b-s2 >/dev/null 2>&1
step train; MSYS_NO_PATHCONV=1 wsl.exe --cd "$(pwd -W)" -e bash training/wsl/s3.sh > "$out/wsl.log" 2>&1 || { step "train-failed"; exit 1; }
step import; (cd training/wsl && ollama create scriber-ir:4b-s3 -f Modelfile.4b-s3) > "$out/import.log" 2>&1 || { step "import-failed"; exit 1; }
step gates
uv run scriber-evals evals/cases/dev.yaml --models scriber-ir:4b-s3 scriber-ir:4b-s2 > "$out/gate-dev.log" 2>&1
uv run scriber-evals evals/cases/m1.yaml --models scriber-ir:4b-s3 scriber-ir:4b-s2 > "$out/gate-m1.log" 2>&1
for m in scriber-ir:4b-s3 scriber-ir:4b-s2; do uv run scriber-grounded --model $m > "$out/gate-grounded-${m##*:}.log" 2>&1; done
uv run scriber-parity M6-SHOWCASE --model scriber-ir:4b-s3 > "$out/showcase-s3.log" 2>&1
step done
