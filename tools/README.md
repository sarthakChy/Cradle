# GTA SA Recording Tools

These scripts reuse Cradle's built-in window capture and record local gameplay sessions for later alignment and training.

## Files

- `record_gta_sa_video.py` records only video.
- `record_gta_sa_inputs.py` records keyboard hooks, mouse hooks, raw mouse deltas, and state snapshots to JSONL.
- `record_gta_sa_session.py` records both video and input in one session folder.

## Recommended Command

```bash
python tools/record_gta_sa_session.py --env-config conf/env_config_gta_sa_dxwnd.json
```

This is the recommended command for the current DxWnd setup.

## Output

Each run writes into a session directory under `runs/<YYYY-MM-DD>/time_start_<HH-MM-SS-%f>/` by default:

- `video.mp4`
- `inputs.jsonl`
- `frame_timeline.jsonl`
- `manifest.json`

## Mapping A Session

After recording a session, run the mapper to extract frames and build the aligned dataset:

```bash
python tools/map_gta_sa_session.py
```

By default, the mapper finds the latest complete session under `runs/`.
You can still override it with `--session-dir` if needed.
It also samples observations at 200 ms intervals by default, so the output is a 5 Hz dataset instead of one row per rendered frame.

The mapper expects these files inside a session directory:

- `video.mp4`
- `inputs.jsonl`
- `frame_timeline.jsonl`
- `manifest.json`

It writes these outputs into `mapped_dataset/` by default:

- `mapped_frames.jsonl`
- `sync_report.txt`
- `frames/frame_00000.jpg` and onward

## Stop Key

The input recorder stops the full session when you press `F10`.

## Logger Shape

The input log is now closer to Lumine's style than a plain keypress dump:

- low-level Windows hooks capture keyboard and absolute mouse state,
- raw input captures relative mouse movement,
- every record carries the current held-key and held-button state,
- periodic state snapshots are emitted at a near-frame polling interval,
- timestamps are taken at capture time with the Windows time API.

The session manifest and frame timeline make offline alignment deterministic:

- `manifest.json` stores the session anchor, video start anchor, and file paths.
- `frame_timeline.jsonl` stores one timestamped record per captured frame.