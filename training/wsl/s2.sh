#!/usr/bin/env bash
# S2 on the 4B, end to end: base weights, QLoRA, merge, bf16 GGUF, Q4_K_M into the repo's data folder
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
cd ~/partwright-train
source .venv/bin/activate
run=runs/s2-4b
out=$repo/data/training/s2-4b/run
mkdir -p "$run" "$out"
[ -f ~/models/Qwen3.5-4B/config.json ] || hf download Qwen/Qwen3.5-4B --local-dir ~/models/Qwen3.5-4B > ~/models/download-4b.log 2>&1
echo "train $(date)"
python train.py --data $repo/data/training/s2/train.jsonl --model ~/models/Qwen3.5-4B --out "$run" \
  --load-4bit --max-seq 4096 --batch 1 --accum 8 --save-steps 100 --no-merge > "$run/train.log" 2>&1
echo "merge $(date)"
python $repo/training/wsl/merge.py --lora "$run/lora" --out "$run/merged" > "$run/merge.log" 2>&1
echo "convert $(date)"
python llama.cpp/convert_hf_to_gguf.py "$run/merged" --outtype bf16 --outfile "$run/s2-4b-bf16.gguf" > "$run/convert.log" 2>&1
llama.cpp/build/bin/llama-quantize "$run/s2-4b-bf16.gguf" "$out/partwright-ir-4b-s2-q4_k_m.gguf" Q4_K_M > "$run/quantize.log" 2>&1
rm -rf "$run/merged" "$run/s2-4b-bf16.gguf"
echo "done $(date)"
