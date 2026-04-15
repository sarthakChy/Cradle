from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert mapped GTA SA frames into Gemma-ready training JSONL.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to mapped_frames.jsonl produced by tools/map_gta_sa_session.py.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSONL path. Defaults to <input_dir>/gemma_train.jsonl.",
    )
    parser.add_argument(
        "--instruction",
        default="You are an AI agent playing GTA San Andreas. Predict the next 6 actions.",
        help="Instruction text written after the <image> token.",
    )
    parser.add_argument(
        "--image-root",
        default=None,
        help="Optional root directory for resolving frame_path. Defaults to the input directory.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def dump_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def is_noop(record: dict[str, Any]) -> bool:
    action_sequence = record.get("action_sequence", {})
    chunks = action_sequence.get("chunks", [])

    if int(action_sequence.get("mouse_dx", 0)) != 0 or int(action_sequence.get("mouse_dy", 0)) != 0:
        return False

    observation_state = record.get("observation_state", {})
    if observation_state.get("held_keys") or observation_state.get("held_buttons"):
        return False

    for chunk in chunks:
        if chunk.get("token_text"):
            return False
        if int(chunk.get("mouse_dx", 0)) != 0 or int(chunk.get("mouse_dy", 0)) != 0:
            return False
        if chunk.get("held_buttons") or chunk.get("held_keys"):
            return False

    return True


def build_example(record: dict[str, Any], image_path: Path, instruction: str) -> dict[str, Any]:
    target = "" if is_noop(record) else str(record.get("action_text", "")).strip()

    return {
        "messages": [
            {
                "role": "user",
                "content": f"<image>\n{instruction}",
            },
            {
                "role": "assistant",
                "content": target,
            },
        ],
        "images": [str(image_path.resolve())],
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    image_root = Path(args.image_root) if args.image_root is not None else input_path.parent
    output_path = Path(args.output) if args.output is not None else input_path.parent / "gemma_train.jsonl"

    records = load_jsonl(input_path)
    examples: list[dict[str, Any]] = []
    noop_rows = 0

    for record in records:
        frame_path = record.get("frame_path")
        if not frame_path:
            continue

        image_path = (image_root / frame_path).resolve()
        if not image_path.exists():
            raise FileNotFoundError(f"Missing frame image: {image_path}")

        if is_noop(record):
            noop_rows += 1

        examples.append(build_example(record, image_path, args.instruction))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dump_jsonl(output_path, examples)

    print(f"Input records:  {len(records)}")
    print(f"Examples out:   {len(examples)}")
    print(f"Noop rows:      {noop_rows}")
    print(f"Output JSONL:   {output_path}")


if __name__ == "__main__":
    main()