# GTA SA Video and Log Alignment

This note describes how to line up the recorded `video.mp4` with `inputs.jsonl` for GTA SA sessions.

## What Each Artifact Means

- `video.mp4` is a continuous real-time capture. Its first frame is the video time origin, so the playback timeline starts at `0.00s`.
- `inputs.jsonl` is an event stream. Each record contains wall-clock fields and relative timing fields:
  - `session_start_wall_time_utc` on the first record.
  - `wall_time_utc` on every record.
  - `timestamp_ns` on every record.
  - `elapsed_ms` on every record.

## Core Idea

Use one shared session origin, then express both streams relative to that origin.

- For video: frame time is relative to the first frame.
- For input events: `elapsed_ms` is already relative to the logger start, while `timestamp_ns` and `wall_time_utc` give absolute time.

## Practical Mapping

The simplest mapping is:

```text
video_time_ms = frame_index / video_fps * 1000
event_time_ms = elapsed_ms
```

If the video and log start at slightly different moments, add a start offset:

```text
video_time_ms = (frame_index / video_fps * 1000) + video_start_offset_ms
```

Where `video_start_offset_ms` is the difference between the video capture start and the log start.

## Recommended Session Model

For the cleanest alignment, treat the first `session_start` record as the canonical session marker and store one extra metadata value for the video start time.

Recommended session metadata:

- `session_start_wall_time_utc`
- `video_start_wall_time_utc`
- `video_fps`
- `input_poll_interval_ms`

With that metadata, the mapping becomes:

```text
event_offset_ms = (event_wall_time_utc - session_start_wall_time_utc)
video_offset_ms = (frame_wall_time_utc - video_start_wall_time_utc)
```

Then match events to frames by nearest timestamp, or by the interval containing the event time.

## How To Sync In Practice

1. Use `session_start_wall_time_utc` as the root anchor.
2. Use `elapsed_ms` for quick ordering inside `inputs.jsonl`.
3. Use `video_fps` to estimate the frame index for any event.
4. If exact frame matching matters, record a small session manifest with the video start wall time.

Example:

- If `video_fps = 30`, frame 90 is roughly `3000 ms` after the first video frame.
- If an input record has `elapsed_ms = 3125`, it belongs near video frame `94`.

## Important Caveat

The recorder still does not write explicit per-frame timestamps into the MP4 itself. The container timeline is still FPS-based, not timestamp-embedded.

## What The Manifest And Timeline Add

Each session now writes a `manifest.json` beside the outputs with:

- `session_start_wall_time_utc`
- `video_start_wall_time_utc`
- `video_start_offset_ms`
- `video_fps`
- `input_poll_interval_ms`
- `inputs_path`
- `video_path`

It also writes a `frame_timeline.jsonl` sidecar with one record per captured frame:

- `frame_index`
- `frame_wall_time_utc`
- `frame_elapsed_ms`
- `session_elapsed_ms`

This removes the main ambiguity by giving you both anchors and an explicit per-frame timeline in one place.

The mapper also builds two frame-level views:

- `observation_state`: the aligned state snapshot for what the agent sees now.
- `action_sequence`: the next control sequence to execute after that frame.

## Remaining Limitation

The MP4 itself still has no per-frame wall-clock metadata. But because the sidecar records each frame with wall time and elapsed time, exact offline frame-to-event matching is now practical and repeatable.

## How To Map Exactly

1. Use `frame_wall_time_utc` or `frame_elapsed_ms` from `frame_timeline.jsonl` for the video stream.
2. Use `elapsed_ms` or `timestamp_ns` from `inputs.jsonl` for the input stream.
3. Convert both to the same origin using `session_start_wall_time_utc` and the recorded `video_start_offset_ms`.
4. Use `observation_state` for the current context and `action_sequence` for the training target.
5. Match each input record to the nearest frame or the frame interval containing that timestamp.

That is enough for a clean dataset build without relying on the MP4 container for timing.

## Which One Is Better For Training?

For imitation learning, the Lumine-like `action_sequence` is the better target because it predicts the next 200 ms of control, split into 33 ms subchunks, instead of only the nearest state snapshot.

The nearest-snapshot `observation_state` is still useful as context, debugging, and sanity checking, but it is not the main training target.