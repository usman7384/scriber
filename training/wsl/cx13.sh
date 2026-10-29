#!/usr/bin/env bash
# CX-13 end to end: house-style corpus, QLoRA on Qwen3.5-0.8B, merge, bf16 GGUF, Q8_0 into the repo's data folder
set -euo pipefail
repo=/mnt/d/Projects/bye-kyrall
data=$repo/data/training/cx13
model=$repo/data/models/Qwen3.5-0.8B
run=runs/cx13-0.8b
out=$data/run
# the generator needs the Windows workspace (OCCT kernel), so it runs there through WSL interop
[ -f "$data/train.jsonl" ] || powershell.exe -NoProfile -Command "Set-Location D:\\Projects\\bye-kyrall; uv run partwright-conventions --out data/training/cx13"
cd ~/partwright-train
source .venv/bin/activate
mkdir -p "$run" "$out"
[ -f "$model/config.json" ] || hf download Qwen/Qwen3.5-0.8B --local-dir "$model" > "$run/download.log" 2>&1
echo "train $(date)"
python train.py --data "$data/train.jsonl" --model "$model" --out "$run" --load-4bit --max-seq 4096 --batch 2 --accum 4 --no-merge > "$run/train.log" 2>&1
echo "merge $(date)"
python $repo/training/wsl/merge.py --lora "$run/lora" --out "$run/merged" > "$run/merge.log" 2>&1
echo "convert $(date)"
python llama.cpp/convert_hf_to_gguf.py "$run/merged" --outtype bf16 --outfile "$run/cx13-bf16.gguf" > "$run/convert.log" 2>&1
llama.cpp/build/bin/llama-quantize "$run/cx13-bf16.gguf" "$out/partwright-ir-0.8b-cx13-q8_0.gguf" Q8_0 > "$run/quantize.log" 2>&1
rm -rf "$run/merged" "$run/cx13-bf16.gguf"
echo "done $(date)"
cat <<'EOF'
Then on Windows, from D:\Projects\bye-kyrall (Ollama running, qwen3.5:0.8b-q8_0 pulled):
  cd training\wsl; ollama create partwright-ir:0.8b-cx13 -f Modelfile.0.8b-cx13; cd ..\..
  $env:PARTWRIGHT_CX13_BASE = "qwen3.5:0.8b-q8_0"
  uv run partwright-parity CX-13 --model partwright-ir:0.8b-cx13
EOF
