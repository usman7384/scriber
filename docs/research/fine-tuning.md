# Fine-tuning small Qwen models on 6 GB VRAM

Researched 2026-10-25. No training run was executed in this session (shared GPU, disk budget). Run-time numbers are **estimates** and are labelled as such. Versions come from PyPI today.

## TL;DR

- **Stack: Unsloth 2026.10.8 (Apache-2.0) in WSL2 Ubuntu (Python 3.12)**, with TRL 1.16.0, PEFT 0.21.2, bitsandbytes 0.50.2 and transformers 5.20.2 underneath. Use plain PEFT + TRL on native Windows as the fallback. Skip axolotl 0.19.0 (Linux-oriented, heavier, no advantage at this scale).
- **Toy target: Qwen2.5-Coder-1.5B, LoRA r=16.** The base model is already in the HF cache, so there is no download. Use QLoRA (4-bit) when a sequence is > 2k tokens. Next step: **Qwen3.5-0.8B bf16 LoRA** (~3 GB), which matches the default model family. Unsloth advises **against QLoRA on Qwen3.5**.
- **Export: merge → GGUF Q4_K_M → `ollama create`.** Do not rely on Ollama `ADAPTER`: today's Modelfile reference lists no ADAPTER instruction (checked 2026-10-25).
- **Stop Ollama's resident model before training** (`ollama stop <model>`, or `keep_alive: 0`). It holds up to 5 GB of the 6 GB.

## What fits (6 GB laptop GPU, ~5.8 GB usable, gradient checkpointing on, batch 1 with gradient accumulation)

| Model | Method | VRAM (source) | Seq len that fits | Licence | Verdict |
|---|---|---|---|---|---|
| Qwen2.5-Coder-0.5B | full fine-tune (8-bit Adam) or LoRA | ~4–5 GB full / ~2 GB LoRA (estimate) | 2–4k | Apache-2.0 | CI smoke-train |
| **Qwen2.5-Coder-1.5B** | LoRA bf16 | ~4–5 GB (estimate) | ~2k | Apache-2.0 | **toy pipeline** |
| Qwen2.5-Coder-1.5B | QLoRA 4-bit | ~2.5–3.5 GB (estimate) | 4k | Apache-2.0 | longer-context variant |
| **Qwen3.5-0.8B** | LoRA bf16 | **3 GB** (Unsloth Qwen3.5 guide) | 2–4k | Apache-2.0 | next step (same family as the default) |
| Qwen3.5-2B | LoRA bf16 | **5 GB** (Unsloth) | ≤1k | Apache-2.0 | borderline |
| Qwen3.5-4B | LoRA bf16 | **10 GB** (Unsloth) | — | Apache-2.0 | **does not fit**; QLoRA not recommended for 3.5 |
| Qwen2.5-Coder-3B | QLoRA | ~3.5 GB (Unsloth generic table) | 2k | **Qwen Research Licence** | avoid (licence) |
| Qwen3-4B-Instruct-2507 | QLoRA | ~4–4.5 GB (estimate) | ≤1k | Apache-2.0 | possible, but tight |
| Qwen2.5-Coder-7B | QLoRA | ≥5 GB minimum (Unsloth generic) | <512 | Apache-2.0 | **not practical** on this GPU |

Unsloth figures: [Qwen3.5 fine-tune guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune) (0.8B 3 GB, 2B 5 GB, 4B 10 GB; bf16 LoRA minimums), and the generic QLoRA table quoted in [Pinggy 2026](https://pinggy.io/blog/finetune_and_selfhost_llms_locally_with_unsloth/) (3B ~3.5 GB, 7B ~5 GB, 8B ~6 GB).

## Toy run (estimates)

- Data: 2,000 synthetic `(prompt + context → IR JSON)` pairs, ~600 tokens each, which is about 1.2M tokens per epoch.
- Qwen2.5-Coder-1.5B LoRA on an RTX 3060 Laptop with Unsloth: ~2–3k tokens/s, so **~7–10 min per epoch** (estimate). 0.5B: ~3 min per epoch. Qwen3.5-0.8B: slower than its size suggests because of the custom Gated-DeltaNet kernels (Unsloth notes this). Budget ~10 min.
- Success criterion for the toy run: held-out **schema-valid %** and **compile %** beat the same base model with few-shot prompting, measured by the same eval harness as inference.

## Recipe

```python
# WSL2: uv venv -p 3.12; uv pip install "unsloth==2026.10.8"   (pulls torch+CUDA, trl, peft, bitsandbytes)
from unsloth import FastLanguageModel
from trl import SFTTrainer, SFTConfig

model, tok = FastLanguageModel.from_pretrained(
    "Qwen/Qwen2.5-Coder-1.5B-Instruct",  # or local HF cache path
    max_seq_length=2048,
    load_in_4bit=False,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=16,
    lora_dropout=0,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    use_gradient_checkpointing="unsloth",
)
trainer = SFTTrainer(
    model=model,
    processing_class=tok,
    train_dataset=ds,  # chat-format JSONL
    args=SFTConfig(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        num_train_epochs=1,
        bf16=True,
        logging_steps=10,
        assistant_only_loss=True,
        output_dir="runs/ir-1.5b",
    ),
)
trainer.train()
model.save_pretrained_gguf("out/ir-1.5b", tok, quantization_method="q4_k_m")  # builds llama.cpp (needs cmake, build-essential)
```

The API names follow current Unsloth/TRL docs but have not been run here. Check them against the installed versions.

Ollama import (Windows side):

```
# Modelfile
FROM D:/scriber/models/ir-1.5b/unsloth.Q4_K_M.gguf
TEMPLATE """<copy from: ollama show --modelfile qwen2.5-coder:1.5b>"""
PARAMETER temperature 0
PARAMETER num_ctx 8192
```

Then `ollama create scriber-ir:1.5b-q4 -f Modelfile`. The output is about 1.0 GB.

Alternative without Unsloth: `merge_and_unload()` (PEFT), then llama.cpp `convert_hf_to_gguf.py` and `llama-quantize … Q4_K_M`.

## Disk budget (WSL vhdx lives on C:, 23 GB free)

| Item | Size |
|---|---|
| WSL venv: torch (CUDA) + unsloth + deps | ~6–8 GB (estimate) |
| llama.cpp build for GGUF export | ~0.5 GB |
| Base model (HF cache; already present on the Windows side and readable via `/mnt/c`, or copied) | 0 (present) / 3.1 GB if copied |
| Merged fp16 temp | ~3 GB (delete after export) |
| GGUF Q4_K_M | ~1 GB (move to D:) |

Notes:

- Point `HF_HOME` at the existing Windows cache to avoid duplicates. Expect slower I/O across `/mnt/c`.
- Run `wsl --manage <distro> --set-sparse true` (or compact the vhdx) after cleanup to reclaim C: space.

## Risks

- WSL2 on 16 GB RAM: the default WSL memory cap is 50% (8 GB). Set `.wslconfig memory=10GB` for training and close the browser and IDE.
- Unsloth's native Windows installer exists (2026 guides), but triton and bitsandbytes on Windows remain fragile. WSL is the supported path.
- Laptop thermals: sustained training throttles. Expect ±30% on the estimates.
- Data licence decides whether the resulting weights can be published (see `llm-cad-research.md`).
