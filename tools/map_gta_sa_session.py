from __future__ import annotations

import argparse
import bisect
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map GTA SA frame timeline entries to input snapshots and extract frames.")
    parser.add_argument(
        "--session-dir",
        default=None,
        help="Optional session directory containing manifest.json, frame_timeline.jsonl, inputs.jsonl, and video.mp4. Defaults to the latest session under runs/.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory for the mapped dataset. Defaults to <session-dir>/mapped_dataset/.",
    )
    parser.add_argument(
        "--frame-range",
        default=None,
        help="Optional inclusive frame range as start:end.",
    )
    parser.add_argument(
        "--observation-interval-ms",
        type=float,
        default=200.0,
        help="Observation sampling interval in milliseconds. Default: 200 (5 Hz).",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=95,
        help="JPEG quality for extracted frames. Default: 95",
    )
    parser.add_argument(
        "--warn-ms",
        type=float,
        default=20.0,
        help="Warning threshold in ms for frame/input mismatch. Default: 20",
    )
    parser.add_argument(
        "--bad-ms",
        type=float,
        default=50.0,
        help="Bad threshold in ms for frame/input mismatch. Default: 50",
    )
    parser.add_argument(
        "--action-window-ms",
        type=float,
        default=200.0,
        help="Action target window in milliseconds. Default: 200.",
    )
    parser.add_argument(
        "--action-chunks",
        type=int,
        default=6,
        help="Number of sub-chunks in each action window. Default: 6.",
    )
    parser.add_argument(
        "--mouse-mode",
        choices=["relative", "absolute"],
        default="relative",
        help="Mouse encoding for the action target. Default: relative",
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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_latest_session_dir(runs_root: Path) -> Path:
    if not runs_root.exists():
        raise FileNotFoundError(f"Missing runs directory: {runs_root}")

    candidates: list[tuple[datetime, Path]] = []
    for manifest_path in runs_root.rglob("manifest.json"):
        session_dir = manifest_path.parent
        frame_timeline_path = session_dir / "frame_timeline.jsonl"
        inputs_path = session_dir / "inputs.jsonl"
        video_path = session_dir / "video.mp4"
        if not frame_timeline_path.exists() or not inputs_path.exists() or not video_path.exists():
            continue

        try:
            manifest = load_json(manifest_path)
            session_start_text = manifest.get("session_start_wall_time_utc")
            if session_start_text:
                session_start = datetime.fromisoformat(session_start_text)
            else:
                session_start = datetime.fromtimestamp(session_dir.stat().st_mtime)
        except Exception:
            session_start = datetime.fromtimestamp(session_dir.stat().st_mtime)

        candidates.append((session_start, session_dir))

    if not candidates:
        raise FileNotFoundError(f"No complete session directories found under {runs_root}")

    candidates.sort(key=lambda item: (item[0], item[1].as_posix()))
    return candidates[-1][1]


def parse_frame_range(frame_range: str | None) -> tuple[int, int] | None:
    if frame_range is None:
        return None

    if ":" not in frame_range:
        raise ValueError("--frame-range must be in start:end format")

    start_text, end_text = frame_range.split(":", 1)
    return int(start_text), int(end_text)


def sample_frames_by_interval(frames: list[dict[str, Any]], interval_ms: float) -> list[dict[str, Any]]:
    if interval_ms <= 0:
        raise ValueError("--observation-interval-ms must be greater than 0")

    sampled_frames: list[dict[str, Any]] = []
    last_sampled_ms = -interval_ms

    for frame in frames:
        session_elapsed_ms = float(frame["session_elapsed_ms"])
        if session_elapsed_ms - last_sampled_ms >= interval_ms:
            sampled_frames.append(frame)
            last_sampled_ms = session_elapsed_ms

    return sampled_frames


def build_input_snapshots(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for event in events:
        if event.get("event_type") != "state_snapshot":
            continue

        elapsed_ms = event.get("elapsed_ms")
        if elapsed_ms is None:
            continue

        snapshots.append(
            {
                "elapsed_ms": float(elapsed_ms),
                "held_keys": event.get("held_keys", []),
                "held_buttons": event.get("held_buttons", []),
                "mouse_abs": event.get("mouse_position"),
                "mouse_rel": event.get("relative_mouse_delta", [0, 0]),
            }
        )

    snapshots.sort(key=lambda item: item["elapsed_ms"])
    return snapshots


def build_action_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    action_events: list[dict[str, Any]] = []
    for event in events:
        if event.get("event_type") == "state_snapshot":
            continue

        elapsed_ms = event.get("elapsed_ms")
        if elapsed_ms is None:
            continue

        action_events.append(event)

    action_events.sort(key=lambda item: float(item["elapsed_ms"]))
    return action_events


def normalize_key_token(key_name: str | None) -> str | None:
    if key_name is None:
        return None

    token = str(key_name).strip().lower()
    aliases = {
        "shift": "SHIFT",
        "lshift": "SHIFT",
        "rshift": "SHIFT",
        "ctrl": "CTRL",
        "lctrl": "CTRL",
        "rctrl": "CTRL",
        "alt": "ALT",
        "lalt": "ALT",
        "ralt": "ALT",
        "space": "SPACE",
        "esc": "ESC",
        "enter": "ENTER",
        "tab": "TAB",
        "backspace": "BACKSPACE",
        "delete": "DELETE",
        "insert": "INSERT",
        "home": "HOME",
        "end": "END",
        "page_up": "PAGE_UP",
        "page_down": "PAGE_DOWN",
        "left": "LEFT",
        "right": "RIGHT",
        "up": "UP",
        "down": "DOWN",
        "caps_lock": "CAPS_LOCK",
        "num_lock": "NUM_LOCK",
        "scroll_lock": "SCROLL_LOCK",
        "print_screen": "PRINT_SCREEN",
    }

    if token in aliases:
        return aliases[token]
    if token.startswith("numpad_"):
        return token.replace("numpad_", "NUMPAD_").upper()
    if token.startswith("f") and token[1:].isdigit():
        return token.upper()
    if len(token) == 1 and token.isalnum():
        return token.upper()

    return token.replace(" ", "_").upper()


def normalize_button_token(button_name: str | None) -> str | None:
    if button_name is None:
        return None

    token = str(button_name).strip().lower()
    aliases = {
        "left": "LMB",
        "right": "RMB",
        "middle": "MMB",
        "x1": "X1",
        "x2": "X2",
    }
    return aliases.get(token, token.upper())


def create_input_state() -> dict[str, Any]:
    return {
        "held_keys": set(),
        "held_buttons": set(),
        "mouse_abs": None,
    }


def copy_input_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "held_keys": set(state["held_keys"]),
        "held_buttons": set(state["held_buttons"]),
        "mouse_abs": None if state["mouse_abs"] is None else list(state["mouse_abs"]),
    }


def apply_input_event_to_state(event: dict[str, Any], state: dict[str, Any]) -> None:
    event_type = event.get("event_type")

    if event_type == "keyboard":
        key_token = normalize_key_token(event.get("key"))
        action = event.get("action")
        if key_token is None:
            return
        if action == "down":
            state["held_keys"].add(key_token)
        elif action == "up":
            state["held_keys"].discard(key_token)
        return

    if event_type == "mouse_button":
        button_token = normalize_button_token(event.get("button"))
        action = event.get("action")
        if button_token is None:
            return
        if action == "down":
            state["held_buttons"].add(button_token)
        elif action == "up":
            state["held_buttons"].discard(button_token)
        return

    if event_type == "mouse_absolute":
        x_pos = event.get("x")
        y_pos = event.get("y")
        if x_pos is not None and y_pos is not None:
            state["mouse_abs"] = [int(x_pos), int(y_pos)]


def advance_state_until(action_events: list[dict[str, Any]], action_times: list[float], state: dict[str, Any], cursor: int, limit_ms: float) -> int:
    while cursor < len(action_events) and action_times[cursor] < limit_ms:
        apply_input_event_to_state(action_events[cursor], state)
        cursor += 1
    return cursor


def render_state_tokens(held_keys: list[str], held_buttons: list[str]) -> str:
    tokens = held_keys + held_buttons
    return "" if not tokens else "+".join(tokens)


def normalize_snapshot_tokens(values: list[str], normalizer) -> list[str]:
    normalized: list[str] = []
    for value in values:
        token = normalizer(value)
        if token is not None:
            normalized.append(token)
    return sorted(normalized)


def build_action_sequence_for_frame(
    action_events: list[dict[str, Any]],
    action_times: list[float],
    frame_start_ms: float,
    frame_state: dict[str, Any],
    mouse_mode: str,
    action_window_ms: float,
    action_chunks: int,
    start_cursor: int,
) -> tuple[dict[str, Any], int]:
    window_state = copy_input_state(frame_state)
    chunk_duration_ms = action_window_ms / max(action_chunks, 1)
    window_end_ms = frame_start_ms + action_window_ms
    window_end_index = bisect.bisect_right(action_times, window_end_ms, lo=start_cursor)

    window_cursor = start_cursor
    subchunks: list[dict[str, Any]] = []
    total_rel_dx = 0
    total_rel_dy = 0

    start_abs = None if frame_state["mouse_abs"] is None else list(frame_state["mouse_abs"])

    for chunk_index in range(action_chunks):
        chunk_start_ms = frame_start_ms + (chunk_index * chunk_duration_ms)
        chunk_end_ms = window_end_ms if chunk_index == action_chunks - 1 else (chunk_start_ms + chunk_duration_ms)
        chunk_start_abs = None if window_state["mouse_abs"] is None else list(window_state["mouse_abs"])
        chunk_rel_dx = 0
        chunk_rel_dy = 0
        chunk_event_count = 0

        while window_cursor < window_end_index and action_times[window_cursor] <= chunk_end_ms:
            event = action_events[window_cursor]
            event_type = event.get("event_type")
            chunk_event_count += 1

            if event_type == "mouse_relative":
                delta_x = int(event.get("dx", 0))
                delta_y = int(event.get("dy", 0))
                chunk_rel_dx += delta_x
                chunk_rel_dy += delta_y
                total_rel_dx += delta_x
                total_rel_dy += delta_y

            apply_input_event_to_state(event, window_state)
            window_cursor += 1

        if mouse_mode == "absolute":
            if chunk_start_abs is not None and window_state["mouse_abs"] is not None:
                chunk_mouse_dx = window_state["mouse_abs"][0] - chunk_start_abs[0]
                chunk_mouse_dy = window_state["mouse_abs"][1] - chunk_start_abs[1]
            else:
                chunk_mouse_dx = 0
                chunk_mouse_dy = 0
        else:
            chunk_mouse_dx = chunk_rel_dx
            chunk_mouse_dy = chunk_rel_dy

        subchunks.append(
            {
                "chunk_index": chunk_index,
                "chunk_start_ms": round(chunk_start_ms, 3),
                "chunk_end_ms": round(chunk_end_ms, 3),
                "chunk_duration_ms": round(chunk_end_ms - chunk_start_ms, 3),
                "held_keys": sorted(window_state["held_keys"]),
                "held_buttons": sorted(window_state["held_buttons"]),
                "mouse_dx": chunk_mouse_dx,
                "mouse_dy": chunk_mouse_dy,
                "mouse_abs": None if window_state["mouse_abs"] is None else list(window_state["mouse_abs"]),
                "event_count": chunk_event_count,
                "token_text": render_state_tokens(sorted(window_state["held_keys"]), sorted(window_state["held_buttons"])),
            }
        )

    if mouse_mode == "absolute":
        if start_abs is not None and window_state["mouse_abs"] is not None:
            window_mouse_dx = window_state["mouse_abs"][0] - start_abs[0]
            window_mouse_dy = window_state["mouse_abs"][1] - start_abs[1]
        else:
            window_mouse_dx = 0
            window_mouse_dy = 0
    else:
        window_mouse_dx = total_rel_dx
        window_mouse_dy = total_rel_dy

    action_text = " ; ".join([f"{window_mouse_dx} {window_mouse_dy} 0", *(subchunk["token_text"] for subchunk in subchunks)])

    action_sequence = {
        "window_start_ms": round(frame_start_ms, 3),
        "window_end_ms": round(window_end_ms, 3),
        "window_duration_ms": round(window_end_ms - frame_start_ms, 3),
        "mouse_mode": mouse_mode,
        "mouse_dx": window_mouse_dx,
        "mouse_dy": window_mouse_dy,
        "mouse_abs": None if window_state["mouse_abs"] is None else list(window_state["mouse_abs"]),
        "chunk_duration_ms": round(chunk_duration_ms, 3),
        "chunks": subchunks,
        "action_text": action_text,
        "event_count": sum(subchunk["event_count"] for subchunk in subchunks),
    }

    return action_sequence, window_cursor


def nearest_snapshot(snapshots: list[dict[str, Any]], snapshot_times: list[float], elapsed_ms: float) -> tuple[dict[str, Any], float]:
    if not snapshots:
        raise ValueError("No input snapshots were found in inputs.jsonl")

    index = bisect.bisect_left(snapshot_times, elapsed_ms)
    candidates = []
    if index < len(snapshots):
        candidates.append(index)
    if index > 0:
        candidates.append(index - 1)

    best_index = min(candidates, key=lambda idx: abs(snapshot_times[idx] - elapsed_ms))
    snapshot = snapshots[best_index]
    delta = abs(snapshot["elapsed_ms"] - elapsed_ms)
    return snapshot, delta


def summarize_action_chunk(chunk: dict[str, Any]) -> str:
    parts: list[str] = []

    if chunk["key_downs"]:
        parts.append("key_down=" + "+".join(chunk["key_downs"]))
    if chunk["key_ups"]:
        parts.append("key_up=" + "+".join(chunk["key_ups"]))
    if chunk["button_downs"]:
        parts.append("button_down=" + "+".join(chunk["button_downs"]))
    if chunk["button_ups"]:
        parts.append("button_up=" + "+".join(chunk["button_ups"]))
    if chunk["mouse_dx"] != 0 or chunk["mouse_dy"] != 0:
        parts.append(f"mouse_rel={chunk['mouse_dx']},{chunk['mouse_dy']}")
    if chunk["scroll_x"] != 0 or chunk["scroll_y"] != 0:
        parts.append(f"scroll={chunk['scroll_x']},{chunk['scroll_y']}")
    if chunk["mouse_abs"] is not None:
        parts.append(f"mouse_abs={chunk['mouse_abs'][0]},{chunk['mouse_abs'][1]}")

    return "" if not parts else " | ".join(parts)


def summarize_action_chunk_from_events(action_events: list[dict[str, Any]], start_ms: float, end_ms: float, start_index: int) -> tuple[dict[str, Any], int]:
    chunk = {
        "chunk_start_ms": round(start_ms, 3),
        "chunk_end_ms": round(end_ms, 3),
        "chunk_duration_ms": round(end_ms - start_ms, 3),
        "key_downs": [],
        "key_ups": [],
        "button_downs": [],
        "button_ups": [],
        "mouse_dx": 0,
        "mouse_dy": 0,
        "scroll_x": 0,
        "scroll_y": 0,
        "mouse_abs": None,
        "event_count": 0,
        "action_text": "",
    }

    index = start_index
    while index < len(action_events) and float(action_events[index]["elapsed_ms"]) <= start_ms:
        index += 1

    while index < len(action_events):
        event = action_events[index]
        elapsed_ms = float(event["elapsed_ms"])
        if elapsed_ms > end_ms:
            break

        event_type = event.get("event_type")
        chunk["event_count"] += 1

        if event_type == "keyboard":
            key_name = event.get("key")
            action = event.get("action")
            if action == "down" and key_name is not None:
                chunk["key_downs"].append(key_name)
            elif action == "up" and key_name is not None:
                chunk["key_ups"].append(key_name)
        elif event_type == "mouse_button":
            button_name = event.get("button")
            action = event.get("action")
            if action == "down" and button_name is not None:
                chunk["button_downs"].append(button_name)
            elif action == "up" and button_name is not None:
                chunk["button_ups"].append(button_name)
        elif event_type == "mouse_relative":
            chunk["mouse_dx"] += int(event.get("dx", 0))
            chunk["mouse_dy"] += int(event.get("dy", 0))
        elif event_type == "mouse_absolute":
            x_pos = event.get("x")
            y_pos = event.get("y")
            if x_pos is not None and y_pos is not None:
                chunk["mouse_abs"] = [int(x_pos), int(y_pos)]
        elif event_type == "mouse_scroll":
            delta = int(event.get("delta", 0))
            action = event.get("action")
            if action == "vertical":
                chunk["scroll_y"] += delta
            elif action == "horizontal":
                chunk["scroll_x"] += delta

        index += 1

    chunk["action_text"] = summarize_action_chunk(chunk)
    return chunk, index


def extract_frames(video_path: Path, frames_dir: Path, frame_records: list[dict[str, Any]], jpeg_quality: int) -> dict[int, str]:
    frames_dir.mkdir(parents=True, exist_ok=True)

    wanted = {record["frame_index"] for record in frame_records}
    saved_paths: dict[int, str] = {}

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    try:
        current_index = 0
        while True:
            success, frame = capture.read()
            if not success:
                break

            if current_index in wanted:
                filename = f"frame_{current_index:05d}.jpg"
                out_path = frames_dir / filename
                cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
                saved_paths[current_index] = f"frames/{filename}"

            current_index += 1
    finally:
        capture.release()

    return saved_paths


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    session_dir = Path(args.session_dir) if args.session_dir is not None else find_latest_session_dir(repo_root / "runs")
    output_dir = Path(args.output_dir) if args.output_dir else session_dir / "mapped_dataset"
    frames_dir = output_dir / "frames"
    output_mapped = output_dir / "mapped_frames.jsonl"
    output_report = output_dir / "sync_report.txt"

    manifest_path = session_dir / "manifest.json"
    frame_timeline_path = session_dir / "frame_timeline.jsonl"
    inputs_path = session_dir / "inputs.jsonl"
    video_path = session_dir / "video.mp4"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest.json: {manifest_path}")
    if not frame_timeline_path.exists():
        raise FileNotFoundError(f"Missing frame_timeline.jsonl: {frame_timeline_path}")
    if not inputs_path.exists():
        raise FileNotFoundError(f"Missing inputs.jsonl: {inputs_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"Missing video.mp4: {video_path}")

    manifest = load_json(manifest_path)
    all_frames = load_jsonl(frame_timeline_path)
    events = load_jsonl(inputs_path)
    action_events = build_action_events(events)
    action_times = [float(event["elapsed_ms"]) for event in action_events]
    snapshots = build_input_snapshots(events)
    snapshot_times = [snapshot["elapsed_ms"] for snapshot in snapshots]
    action_window_ms = float(args.action_window_ms)
    action_chunks = int(args.action_chunks)

    frame_range = parse_frame_range(args.frame_range)
    if frame_range is not None:
        start_index, end_index = frame_range
        all_frames = [frame for frame in all_frames if start_index <= frame["frame_index"] <= end_index]

    frames = sample_frames_by_interval(all_frames, float(args.observation_interval_ms))

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("GTA SA Session Mapper + Frame Extractor")
    print("=" * 60)
    print(f"Session:            {manifest['session_dir']}")
    print(f"Video start offset:  {manifest['video_start_offset_ms']:.3f} ms")
    print(f"Video FPS:          {manifest['video_fps']}")
    print(f"Frames loaded:      {len(all_frames)}")
    print(f"Frames sampled:     {len(frames)}")
    print(f"Raw events loaded:  {len(events)}")
    print(f"Input snapshots:    {len(snapshots)}")
    print(f"Observation interval: {float(args.observation_interval_ms):.3f} ms")
    print(f"Action window:      {action_window_ms:.3f} ms / {action_chunks} chunks")
    print(f"Mouse mode:         {args.mouse_mode}")
    print()

    mapped_records: list[dict[str, Any]] = []
    deltas: list[float] = []
    action_event_counts: list[int] = []
    warn_frames: list[int] = []
    bad_frames: list[int] = []

    print("Mapping frames to observation states and action chunks...")
    live_state = create_input_state()
    live_cursor = 0
    for frame_number, frame in enumerate(frames):
        frame_index = int(frame["frame_index"])
        frame_elapsed_ms = float(frame["frame_elapsed_ms"])
        session_elapsed_ms = float(frame["session_elapsed_ms"])

        snapshot, delta_ms = nearest_snapshot(snapshots, snapshot_times, session_elapsed_ms)
        live_cursor = advance_state_until(action_events, action_times, live_state, live_cursor, session_elapsed_ms)
        frame_state = copy_input_state(live_state)
        action_sequence, _ = build_action_sequence_for_frame(
            action_events,
            action_times,
            session_elapsed_ms,
            frame_state,
            args.mouse_mode,
            action_window_ms,
            action_chunks,
            live_cursor,
        )

        record = {
            "frame_index": frame_index,
            "frame_elapsed_ms": round(frame_elapsed_ms, 3),
            "session_elapsed_ms": round(session_elapsed_ms, 3),
            "event_elapsed_ms": round(snapshot["elapsed_ms"], 3),
            "delta_ms": round(delta_ms, 3),
            "observation_state": {
                "held_keys": normalize_snapshot_tokens(snapshot["held_keys"], normalize_key_token),
                "held_buttons": normalize_snapshot_tokens(snapshot["held_buttons"], normalize_button_token),
                "mouse_abs": snapshot["mouse_abs"],
                "mouse_rel": snapshot["mouse_rel"],
            },
            "action_sequence": action_sequence,
            "action_text": action_sequence["action_text"],
            "frame_path": f"frames/frame_{frame_index:05d}.jpg",
        }

        mapped_records.append(record)
        deltas.append(delta_ms)
        action_event_counts.append(action_sequence["event_count"])

        if delta_ms > args.warn_ms:
            warn_frames.append(frame_index)
        if delta_ms > args.bad_ms:
            bad_frames.append(frame_index)

    saved_paths = extract_frames(video_path, frames_dir, mapped_records, args.jpeg_quality)
    for record in mapped_records:
        record["frame_path"] = saved_paths.get(int(record["frame_index"]), record["frame_path"])

    with output_mapped.open("w", encoding="utf-8") as handle:
        for record in mapped_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
    max_delta = max(deltas) if deltas else 0.0
    min_delta = min(deltas) if deltas else 0.0
    warn_count = len(warn_frames)
    bad_count = len(bad_frames)
    active_actions = sum(1 for count in action_event_counts if count > 0)
    mapped_count = len(mapped_records)

    if not mapped_records:
        verdict = "WARNING: No frames mapped. Check your session files."
    elif bad_count == 0 and avg_delta < args.warn_ms:
        verdict = "CLEAN: Alignment looks good."
    elif bad_count < 0.01 * mapped_count:
        verdict = "ACCEPTABLE: <1% bad frames. Minor drift, usable for training."
    else:
        verdict = "WARNING: Significant drift. Investigate bad frames before training."

    report_lines = [
        "=" * 60,
        "GTA SA SESSION SYNC REPORT",
        "=" * 60,
        f"Session dir:          {manifest['session_dir']}",
        f"Session start (UTC):  {manifest['session_start_wall_time_utc']}",
        f"Video start (UTC):    {manifest['video_start_wall_time_utc']}",
        f"Video start offset:   {manifest['video_start_offset_ms']:.3f} ms",
        f"Video FPS:            {manifest['video_fps']}",
        f"Observation interval: {float(args.observation_interval_ms):.3f} ms",
        f"Action window:        {action_window_ms:.3f} ms / {action_chunks} chunks",
        f"Mouse mode:           {args.mouse_mode}",
        "",
        "── Counts ──────────────────────────────────────────────",
        f"Total frames loaded:  {len(all_frames)}",
        f"Frames sampled:       {len(frames)}",
        f"Total raw events:     {len(events)}",
        f"Input snapshots:      {len(snapshots)}",
        f"Mapped records:       {mapped_count}",
        f"Frames extracted:     {len(saved_paths)}",
        "",
        "── Drift Stats ─────────────────────────────────────────",
        f"Min delta:            {min_delta:.3f} ms",
        f"Avg delta:            {avg_delta:.3f} ms",
        f"Max delta:            {max_delta:.3f} ms",
        f"Warn threshold:       {args.warn_ms} ms",
        f"Bad threshold:        {args.bad_ms} ms",
        f"Frames > warn:        {warn_count} / {mapped_count}",
        f"Frames > bad:         {bad_count} / {mapped_count}",
        f"Active action chunks:  {active_actions} / {mapped_count}",
        "",
        "── Verdict ─────────────────────────────────────────────",
        verdict,
        "=" * 60,
    ]

    report_text = "\n".join(report_lines)
    output_report.write_text(report_text + "\n", encoding="utf-8")

    print(f"Mapped JSONL:  {output_mapped}")
    print(f"Report:        {output_report}")
    print()
    print(report_text)
    print()
    print("── Sample: first 3 mapped records ──────────────────────")
    for record in mapped_records[:3]:
        print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()