from __future__ import annotations

import argparse
from datetime import datetime, timezone
import sys
import threading
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cradle.config import Config
from cradle.provider.video.video_recorder import VideoRecordProvider
from tools.record_gta_sa_inputs import InputRecorder
from tools.session_manifest import write_json_manifest


def _focus_game_window(config: Config) -> None:
    env_window = getattr(config, "env_window", None)
    if env_window is not None:
        env_window.activate()
        return

    from cradle.gameio.lifecycle.ui_control import switch_to_environment

    switch_to_environment()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record GTA SA video and input events in one session.")
    parser.add_argument(
        "--env-config",
        default="conf/env_config_gta_sa_dxwnd.json",
        help="Environment config used to resolve the game window region. Default: conf/env_config_gta_sa_dxwnd.json",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional session directory. Defaults to <runs>/<YYYY-MM-DD>/time_start_<HH-MM-SS-%f>/.",
    )
    parser.add_argument(
        "--video-name",
        default="video.mp4",
        help="Video filename inside the session directory. Default: video.mp4",
    )
    parser.add_argument(
        "--inputs-name",
        default="inputs.jsonl",
        help="Input log filename inside the session directory. Default: inputs.jsonl",
    )
    parser.add_argument(
        "--stop-key",
        default="f10",
        help="Key used to stop the input logger. Default: f10",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional recording length in seconds. If omitted, stop with the stop key or Ctrl+C.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = Config()
    config.load_env_config(args.env_config)
    _focus_game_window(config)

    session_start_wall_time_utc = datetime.now(timezone.utc)
    session_start_perf_ns = time.perf_counter_ns()

    session_dir = Path(args.output_dir) if args.output_dir else Path(config.work_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    video_path = session_dir / args.video_name
    input_path = session_dir / args.inputs_name
    timeline_path = session_dir / "frame_timeline.jsonl"
    manifest_path = session_dir / "manifest.json"

    video_recorder = VideoRecordProvider(
        str(video_path),
        timeline_path=str(timeline_path),
        start_wall_time=session_start_wall_time_utc,
        start_perf_ns=session_start_perf_ns,
    )
    input_recorder = InputRecorder(
        input_path,
        stop_key=args.stop_key,
        start_wall_time=session_start_wall_time_utc,
        start_perf_ns=session_start_perf_ns,
    )

    print(f"Session directory: {session_dir}")
    print(f"Recording video to {video_path}")
    print(f"Recording inputs to {input_path}")
    print(f"Recording frame timeline to {timeline_path}")
    print(f"Captured region: {config.env_region}")
    print(f"Press {args.stop_key.upper()} to stop the session." if args.duration is None else f"Stopping automatically after {args.duration} seconds.")

    video_recorder.start_capture()

    input_thread = threading.Thread(target=input_recorder.start, name="Input Recording", daemon=True)
    input_thread.start()

    try:
        if args.duration is None:
            while input_thread.is_alive():
                time.sleep(0.2)
        else:
            time.sleep(max(args.duration, 0.0))
    except KeyboardInterrupt:
        input_recorder.stop_event.set()
    finally:
        input_recorder.stop_event.set()
        input_thread.join(timeout=5)
        input_recorder.close()
        video_recorder.finish_capture()
        manifest_payload = {
            "session_dir": str(session_dir),
            "env_config": str(Path(args.env_config)),
            "video_path": str(video_path),
            "inputs_path": str(input_path),
            "frame_timeline_path": str(timeline_path),
            "session_start_wall_time_utc": session_start_wall_time_utc.isoformat(),
            "video_start_wall_time_utc": video_recorder.video_start_wall_time_utc.isoformat() if video_recorder.video_start_wall_time_utc else None,
            "video_start_offset_ms": (
                round((video_recorder.video_start_perf_ns - session_start_perf_ns) / 1_000_000.0, 3)
                if video_recorder.video_start_perf_ns is not None
                else None
            ),
            "video_fps": video_recorder.fps,
            "input_poll_interval_ms": int(input_recorder.poll_interval_s * 1000),
            "stop_key": args.stop_key,
            "captured_region": list(config.env_region) if config.env_region is not None else None,
        }
        write_json_manifest(manifest_path, manifest_payload)
        print(f"Finished session: {session_dir}")


if __name__ == "__main__":
    main()