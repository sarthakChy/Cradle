from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cradle.config import Config
from cradle.provider.video.video_recorder import VideoRecordProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record GTA SA gameplay using the repo's built-in window capture.")
    parser.add_argument(
        "--env-config",
        default="conf/env_config_gta_sa.json",
        help="Environment config used to resolve the game window region. Default: conf/env_config_gta_sa.json",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path for the output MP4. Defaults to <runs>/<YYYY-MM-DD>/time_start_<HH-MM-SS-%f>/video.mp4.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional recording length in seconds. If omitted, stop with Ctrl+C.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = Config()
    config.load_env_config(args.env_config)

    output_path = Path(args.output) if args.output else Path(config.work_dir) / "video.mp4"
    recorder = VideoRecordProvider(str(output_path))

    print(f"Recording video to {output_path}")
    print(f"Captured region: {config.env_region}")
    print("Press Ctrl+C to stop." if args.duration is None else f"Stopping automatically after {args.duration} seconds.")

    recorder.start_capture()

    try:
        if args.duration is None:
            while True:
                time.sleep(1)
        else:
            time.sleep(max(args.duration, 0.0))
    except KeyboardInterrupt:
        pass
    finally:
        recorder.finish_capture()
        print(f"Finished recording: {output_path}")


if __name__ == "__main__":
    main()