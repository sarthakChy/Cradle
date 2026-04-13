from __future__ import annotations

from pathlib import Path
import sys

if ".venv" not in sys.executable.lower():
    print(
        "Run this script with the project venv: .\\.venv\\Scripts\\python.exe .\\cradle_ollama_test.py",
        file=sys.stderr,
    )
    raise SystemExit(1)

from cradle.provider.llm.ollama import OllamaProvider
from cradle.utils.encoding_utils import encode_data_to_base64_path


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = REPO_ROOT / "conf" / "ollama_config.json"
DEFAULT_IMAGE = REPO_ROOT / "res" / "icons" / "pink_mouse.png"


def run_text_test(provider: OllamaProvider) -> None:
    text_message, text_info = provider.create_completion([
        {"role": "system", "content": [{"type": "text", "text": "Reply with exactly one word: ok"}]},
        {"role": "user", "content": [{"type": "text", "text": "Say ok"}]},
    ])
    print(f"TEXT: {text_message.strip()}")
    print(f"TEXT_INFO: {text_info}")


def run_vision_test(provider: OllamaProvider, image_path: Path) -> None:
    encoded_image = encode_data_to_base64_path(str(image_path))[0]
    vision_message, vision_info = provider.create_completion([
        {"role": "system", "content": [{"type": "text", "text": "Describe the image in one short sentence."}]},
        {"role": "user", "content": [
            {"type": "text", "text": "What is shown here?"},
            {"type": "image_url", "image_url": {"url": encoded_image}},
        ]},
    ])
    print(f"VISION: {vision_message.strip()}")
    print(f"VISION_INFO: {vision_info}")


def main() -> int:
    config_path = DEFAULT_CONFIG
    image_path = DEFAULT_IMAGE

    if not config_path.exists():
        print(f"Missing config: {config_path}", file=sys.stderr)
        return 1

    if not image_path.exists():
        print(f"Missing test image: {image_path}", file=sys.stderr)
        return 1

    provider = OllamaProvider()
    provider.init_provider(str(config_path))

    print(f"MODEL: {provider.llm_model}")
    print(f"EMBED_MODEL: {provider.embedding_model}")

    run_text_test(provider)
    run_vision_test(provider, image_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())