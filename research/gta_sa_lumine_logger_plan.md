# GTA SA Logger Plan Based on Lumine

This note defines the logging side of the GTA San Andreas data pipeline. The repo already has usable video capture under [tools/record_gta_sa_video.py](../tools/record_gta_sa_video.py), so this document focuses on the input logger.

## What Lumine Does

Lumine uses a standardized recording setup and captures two synchronized streams:

- video recorded with OBS at 1080p, 60 fps, 10,000 kbps, saved as `mkv`,
- keyboard and mouse input logged at the OS level.

The paper makes one point that matters most for GTA SA: mouse input is not enough if you only record a single representation. Lumine records both:

- absolute cursor positions for GUI-style interaction,
- relative mouse movement for overworld 3D camera control.

It also timestamps hook-captured events with a high-resolution clock instead of relying on coarse timestamps.

## What We Are Doing Here

The current repo path is split into two parts:

- video capture is handled by the repo-native recorder under [tools/](../tools/),
- input logging now follows the Lumine idea more closely via Windows hooks and Raw Input.

The first version of the logger was an event-only recorder. That was useful, but it was not close enough to Lumine for 3D gameplay data.

The revised direction is:

1. keep the repo-native video capture,
2. log keyboard state and mouse state together,
3. add periodic state snapshots,
4. use low-level Windows hooks and raw mouse input in the logger.

## Current Logger Shape

The current logger in [tools/record_gta_sa_inputs.py](../tools/record_gta_sa_inputs.py) is now a Windows-specific bridge toward the paper-style setup.

It records:

- low-level keyboard hook events,
- low-level absolute mouse hook events,
- raw relative mouse movement,
- mouse button presses and scroll events,
- periodic snapshots of the held keys, held buttons, mouse position, and accumulated raw delta,
- precise timestamps for every record.

That gives us a usable session trace now while staying aligned with the Lumine logging pattern.

## Target Logger Design

The logger we actually want for GTA SA should look more like this:

- keyboard hooks for reliable press and release capture,
- mouse hooks for absolute pointer state in menus and UI,
- raw relative mouse deltas for 3D camera movement,
- high-resolution timestamps for every event,
- synchronized session start and stop with the video recorder,
- one output folder per run.

For GTA SA, this matters because the same physical mouse motion can mean different things depending on the state:

- in menus, absolute position matters,
- in the overworld, relative motion matters more.

## Tools We Are Using

- [tools/record_gta_sa_video.py](../tools/record_gta_sa_video.py): repo-native video capture.
- [tools/record_gta_sa_inputs.py](../tools/record_gta_sa_inputs.py): current Windows logger, now with hooks, Raw Input, and held-state snapshots.
- [tools/record_gta_sa_session.py](../tools/record_gta_sa_session.py): single-command session launcher.
- Win32 hooks and Raw Input: the current logger backend.

## Why This Order

The repo-native video capture is already good enough, so there is no reason to replace it with OBS.

The logger is the part worth improving because that is where training quality is won or lost. If the mouse data is incomplete, the dataset will be weak even if the video is perfect.

## Next Step

Keep hardening the Windows-specific logger so it stays aligned with Lumine:

- preserve the hook/raw-input split,
- verify timestamp fidelity and alignment with video,
- keep the session format stable for dataset generation,
- keep the snapshot interval near the frame rate, with 10 ms as a practical default unless you have a specific reason to sample faster.

That is the cleanest path if the goal is the best training data rather than the fastest prototype.