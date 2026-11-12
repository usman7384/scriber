import argparse
from pathlib import Path

from unsloth import FastLanguageModel


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lora", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    # loading the base in 4-bit and merging shard by shard keeps a 4B merge inside WSL's 7 GB of RAM
    model, processor = FastLanguageModel.from_pretrained(str(args.lora), max_seq_length=4096, load_in_4bit=True)
    tok = getattr(processor, "tokenizer", processor)
    model.save_pretrained_merged(str(args.out), tok, save_method="merged_16bit", maximum_memory_usage=0.5)


if __name__ == "__main__":
    main()
