# GTA SA Recording Guide

This is the practical setup for recording gameplay and logging input timestamps for dataset collection.

## What you need

- OBS for the video capture.
- The input logger in [tools/record_gta_sa_inputs.py](../tools/record_gta_sa_inputs.py).
- The dependencies from [requirements.txt](../requirements.txt).

## What to record

Record two things at the same time:
- Gameplay video in OBS.
- Keyboard and mouse input events in the JSONL logger.

For the first pass, this is enough.

## Recommended recording flow

1. Create a new run folder, for example `runs/<timestamp>/`.
2. Start OBS and begin recording the game window.
3. Start the input logger in a terminal.
4. Play GTA SA normally.
5. Press `F10` to stop the logger.
6. Stop OBS recording.
7. Keep the video file and the JSONL file together in the same run folder.

## Example command

```powershell
python .\tools\record_gta_sa_inputs.py --output .\runs\<run_id>\inputs.jsonl
```

## What the logger stores

The logger writes one JSON object per line with:
- session start and end markers,
- keyboard key down/up events,
- mouse move events with coordinates and deltas,
- mouse button events,
- mouse scroll events,
- high-resolution timestamps,
- wall-clock UTC timestamps.

## Important note about GTA SA

For menus and UI screens, this logger is usually enough.

For 3D camera control, GTA SA may capture mouse input in a way that is not fully visible through normal desktop-level hooks. If you later need exact raw relative deltas for camera motion, the next step is a Windows Raw Input logger. For now, this logger is a good local-first starting point and is enough to get the dataset pipeline moving.

## Suggested run convention

Use one folder per episode:

```text
runs/
  2026-04-14_001/
    video.mp4
    inputs.jsonl
    notes.txt
```

## Good recording habits

- Keep the game in the same resolution for every run.
- Keep OBS settings stable across recordings.
- Use the same stop key every time.
- Write the task you are attempting in the run notes.
- Keep failure runs as well as success runs.

## Next step after recording

Once you have the raw video and the input JSONL, the next step is to build a small converter that:
- aligns the logs,
- separates GUI and 3D states,
- and emits training samples in the GTA SA dataset format.
