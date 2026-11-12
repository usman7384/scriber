import argparse
import json
from pathlib import Path
from typing import Any

from unsloth import FastLanguageModel  # isort: skip  (must be imported before transformers)
import torch
from datasets import Dataset
from trl import SFTConfig, SFTTrainer
from unsloth.chat_templates import train_on_responses_only

TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def load(path: Path, render: Any, max_chars: int) -> Dataset:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    texts = [render(r["messages"]) for r in rows]
    return Dataset.from_dict({"text": [t for t in texts if len(t) <= max_chars]})


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    p.add_argument("--max-seq", type=int, default=4096)
    p.add_argument("--epochs", type=float, default=1.0)
    p.add_argument("--rank", type=int, default=16)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--accum", type=int, default=4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-steps", type=int, default=-1)
    p.add_argument("--save-steps", type=int, default=0, help="keep a resumable checkpoint every N steps")
    p.add_argument("--load-4bit", action="store_true", help="QLoRA: base weights in 4-bit, for models that do not fit in bf16")
    p.add_argument("--no-merge", action="store_true", help="save only the LoRA adapter")
    args = p.parse_args()

    model, processor = FastLanguageModel.from_pretrained(
        args.model, max_seq_length=args.max_seq, load_in_4bit=args.load_4bit, load_in_16bit=not args.load_4bit
    )
    tok = getattr(processor, "tokenizer", processor)
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.rank,
        lora_alpha=args.rank,
        lora_dropout=0,
        bias="none",
        target_modules=TARGETS,
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
        max_seq_length=args.max_seq,
    )

    def render(messages: list[dict[str, str]]) -> str:
        text: str = tok.apply_chat_template(messages, tokenize=False, enable_thinking=False)
        return text

    data = load(args.data, render, max_chars=args.max_seq * 3)
    print(f"{len(data)} samples; first:\n{data[0]['text'][-400:]}")
    trainer = SFTTrainer(
        model=model,
        processing_class=tok,
        train_dataset=data,
        args=SFTConfig(
            dataset_text_field="text",
            max_length=args.max_seq,
            per_device_train_batch_size=args.batch,
            gradient_accumulation_steps=args.accum,
            num_train_epochs=args.epochs,
            max_steps=args.max_steps,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_ratio=0.03,
            logging_steps=10,
            bf16=True,
            optim="adamw_8bit",
            seed=args.seed,
            output_dir=str(args.out / "checkpoints"),
            save_strategy="steps" if args.save_steps else "no",
            save_steps=args.save_steps or 500,
            save_total_limit=2,
            report_to="none",
        ),
    )
    trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n", response_part="<|im_start|>assistant\n")
    stats = trainer.train()
    metrics = {**stats.metrics, "peak_reserved_gb": round(torch.cuda.max_memory_reserved() / 2**30, 2)}
    (args.out / "train_stats.json").write_text(json.dumps(metrics, indent=2))
    model.save_pretrained(str(args.out / "lora"))
    tok.save_pretrained(str(args.out / "lora"))
    if not args.no_merge:
        model.save_pretrained_merged(str(args.out / "merged"), tok, save_method="merged_16bit")


if __name__ == "__main__":
    main()
