# GTA SA Recording And Mapping vs Lumine

This note compares the current Cradle GTA SA capture and mapping pipeline against the Lumine recipe.
It focuses on the actual numbers, the data shape, and the parts of the mapping logic that are intentionally different.

## Short Answer

Lumine is built around a 5 Hz observation / 30 Hz action design with a 200 ms action window split into 6 x 33 ms chunks.
Our current GTA SA pipeline is different:

- video is recorded at 30 fps, not 60 fps,
- input state snapshots are polled every 10 ms, not 5 ms,
- the latest mapping default is one frame-sized action window, 33.333 ms, not 200 ms,
- the latest mapping default is 1 chunk, not 6 chunks,
- the current output is frame-by-frame, not a 5 Hz observation stream,
- mouse mode is still a session-wide switch, not a per-scene GUI/overworld classifier.

That means our pipeline is currently more practical and easier to train from locally, but it is not a paper-faithful copy of Lumine.

## Lumine Baseline

From the research note in this repo, Lumine's important numbers are:

| Area | Lumine |
| --- | --- |
| Recording resolution | 1920 x 1080 |
| Recording frame rate | 60 fps |
| Recording bitrate | 10,000 kbps |
| Recording container | mkv |
| Observation cadence | 5 Hz |
| Observation period | 200 ms |
| Action chunking | 6 chunks per action window |
| Chunk duration | about 33.3 ms |
| Raw mouse polling | about 5 ms |
| Mouse representation | both absolute and relative, chosen by scene |

The important structure is not just the numbers. Lumine separates perception and control:

- one visual observation every 200 ms,
- six finer-grained action chunks inside that same 200 ms window,
- dynamic mouse encoding depending on whether the scene is GUI or 3D overworld,
- textual action serialization that is meant to be directly tokenized.

## Our Current Recording

The latest GTA SA session captured by this repo had the following values in its manifest:

| Area | Current session |
| --- | --- |
| Environment config | `conf/env_config_gta_sa_dxwnd.json` |
| Session start | 2026-04-14T04:31:26.685711+00:00 |
| Video start | 2026-04-14T04:31:27.944415+00:00 |
| Video start offset | 1259.58 ms |
| Video frame rate | 30 fps |
| Input poll interval | 10 ms |
| Captured region | 806 x 629 |

The current recording stack is also different in form:

- video is produced by the repo-native `VideoRecordProvider`, not OBS,
- the container is `video.mp4`, not `mkv`,
- the recording is continuous real-time capture,
- `inputs.jsonl` stores events plus periodic state snapshots,
- `frame_timeline.jsonl` stores one timestamped record per captured frame,
- `manifest.json` stores the session anchors and capture metadata.

In the latest validated session, the raw data volume was:

| Metric | Value |
| --- | --- |
| Frames | 3126 |
| Raw input events | 19962 |
| State snapshots | 6571 |
| Approximate video length | 104.2 s |

## Our Current Mapping

The mapper now uses the session frame timeline as the primary anchor and maps one record per frame.
In the latest session, the mapping output was:

| Metric | Value |
| --- | --- |
| Mapped records | 3126 |
| Frames extracted | 3126 |
| Average frame-to-snapshot delta | 4.012 ms |
| Maximum frame-to-snapshot delta | 55.954 ms |
| Frames over bad threshold | 1 |
| Active action chunks | 1001 |

The current default mapping policy is:

- action window = one frame interval, 33.333 ms,
- action chunks = 1 by default,
- observation_state = nearest input snapshot for the frame,
- action_sequence = the next control slice after that frame,
- action_text = plain semicolon-delimited text,
- empty chunks serialize as blank segments, not `NOOP`.

This is a deliberate change from the earlier Lumine-like 200 ms / 6 chunk default.
The reason is simple: at 30 fps, a 200 ms future window spans about 6 frames.
If every frame predicted the next 200 ms, each input event would be duplicated across roughly 6 adjacent training examples.
That overlap is a training problem for this dataset shape.

## Exact Differences That Matter

### 1. Observation density

Lumine: 5 Hz observations, one sample every 200 ms.

Current pipeline: 30 fps video mapping, one mapped record per frame.

That means our observation side is about 6x denser than Lumine for the same wall-clock duration.
It gives more samples, but it is not the same training distribution.

### 2. Action horizon

Lumine: one observation corresponds to a 200 ms action horizon split into 6 x 33 ms chunks.

Current pipeline: the default action horizon is one frame, 33.333 ms, split into 1 chunk.

This is the biggest structural difference.
Lumine predicts a future control window.
Our current default predicts the immediate next frame-sized control slice.

### 3. Input polling

Lumine: about 5 ms polling for raw mouse movement.

Current pipeline: 10 ms polling for state snapshots.

So Lumine keeps a finer-grained hardware timeline.
Our recorder is still high-frequency, but it is coarser than Lumine by a factor of 2 on the polling side.

### 4. Mouse handling

Lumine: scene-aware mouse encoding.
GUI uses absolute cursor movement.
3D overworld uses relative movement.

Current pipeline: a global `--mouse-mode` flag decides the mode for the whole session.
Default is `relative`.

This is an intentional simplification.
It is not wrong for 3D gameplay, but it is less expressive than Lumine when sessions mix menus and gameplay.

### 5. Action text format

Lumine: special action serialization that is designed to be directly tokenized, with explicit chunk structure.

Current pipeline: plain ASCII semicolon-delimited text.
The mapper normalizes key and button tokens, but it does not yet use Lumine-style special boundary tokens.

Example current output shape:

```text
-29 -5 0 ; 
```

That means the mouse delta is encoded, but an empty chunk is left blank instead of being rendered as a token like `NOOP`.

### 6. Capture setup

Lumine: standardized 1080p / 60 fps / 10,000 kbps capture, typically with OBS and a stable desktop setup.

Current pipeline: DXWnd session capture with a 806 x 629 captured region in the latest run.
This is smaller, more local, and more practical for the current setup, but it is not the same recording standard.

## What We Are Doing Better For This Project

The current design is not trying to copy Lumine blindly.
It is trying to produce a usable GTA SA dataset on a local machine.

The main advantages of the current design are:

- fewer alignment assumptions,
- explicit per-frame timeline records,
- a manifest that records the session start and video start anchors,
- frame-by-frame output that is easy to inspect,
- a mapping pipeline that is easier to debug on real sessions,
- normalized key and button tokens so observation and action vocabularies match.

## What We Are Still Missing Relative To Lumine

The main gaps are:

- no scene classifier that automatically switches between GUI and overworld mouse modes,
- lower recording resolution than the Lumine baseline,
- lower recording frame rate than the Lumine baseline,
- coarser input polling than the Lumine baseline,
- no formal 5 Hz observation / 30 Hz action split in the default export,
- no special action boundary tokens yet.

## Practical Interpretation

If the goal is to mimic Lumine as closely as possible, the target should be:

- 60 fps recording,
- 5 ms input polling,
- 200 ms observation windows,
- 6 x 33 ms action chunks,
- scene-aware mouse routing,
- token-friendly action strings.

If the goal is to build a local GTA SA dataset that is easy to generate and verify now, the current pipeline is better aligned with that goal:

- 30 fps capture,
- 10 ms polling,
- one frame per sample,
- one frame-sized action horizon by default,
- deterministic offline alignment through `manifest.json` and `frame_timeline.jsonl`.

## What Changes If We Record At 60 FPS

Increasing recording FPS to 60 does not change the game itself, but it changes the time scale of the dataset quite a bit.

### New frame math

At 60 fps:

- one frame lasts 16.667 ms instead of 33.333 ms,
- the number of recorded frames doubles for the same wall-clock duration,
- the visual timeline becomes twice as dense,
- the same motion is captured with half the time gap between frames.

For the latest session length of about 104.2 seconds, that means:

| Metric | At 30 fps | At 60 fps |
| --- | --- | --- |
| Frames for the same duration | 3126 | about 6252 |
| Frame interval | 33.333 ms | 16.667 ms |
| Samples per second | 30 | 60 |

### What happens to mapping windows

If we keep the current mapper's default of one frame-sized action window, the default window should also halve:

- current default window at 30 fps: 33.333 ms,
- equivalent default window at 60 fps: 16.667 ms.

If instead we keep a 33.333 ms action window at 60 fps, then each action target spans about 2 video frames.
That can be useful if we want a little more prediction horizon, but it is no longer truly "one frame per label".

If we restore a Lumine-style 200 ms action horizon at 60 fps, then one target window spans about 12 video frames instead of 6.
That is the key scaling change:

| Window | At 30 fps | At 60 fps |
| --- | --- | --- |
| 33.333 ms | 1 frame | 2 frames |
| 200 ms | 6 frames | 12 frames |

### What happens to data volume

For the same playtime, 60 fps roughly doubles:

- the number of extracted frames,
- the number of frame-level training rows if we still export one row per frame,
- the amount of disk space needed for images,
- the amount of alignment work during mapping.

It does not automatically double the input event log, because input polling is still 10 ms unless we change that too.

### Why 60 fps is worth considering

This is the part that matters for the "movement prediction" logic you mentioned.

Lumine's advantage is not only that it has more chunks in the action string.
It is that the observation and action cadence are designed together so the model can predict a short future control horizon smoothly.

At 60 fps, we get:

- finer visual temporal resolution,
- less visual aliasing during fast camera motion,
- smoother frame-to-frame interpolation in the dataset,
- more natural support for short-horizon action prediction.

So if we keep the resolution the same but move the recording FPS from 30 to 60, the pipeline becomes closer to the kind of temporal granularity that makes Lumine-style control feel responsive.
The tradeoff is that the raw dataset becomes bigger and the label-overlap problem becomes more severe if we continue to map every frame independently with a long future window.

### Practical recommendation

If we switch the recorder to 60 fps, the cleanest choices are:

1. Keep the current frame-by-frame export, but reduce the default action window to 16.667 ms so labels stay one-to-one with frames.
2. Keep a longer action horizon, but stop exporting every single frame as a separate training row.
3. Reintroduce a Lumine-like 200 ms / 6-chunk target only when we also add an observation sampler that selects frames at a lower cadence.

That is the main design point: 60 fps helps a lot, but the action window and sampling policy must be updated with it, otherwise the dataset will become redundant very quickly.

## What Changes If The Game Is Actually 25 FPS

If the game is rendering a stable 25 unique frames per second, that changes the recording recommendation again.

### The duplicate-frame problem

If video capture runs at 30 fps while the game only produces 25 unique frames per second, the recorder has to fill the extra 5 frames every second somehow.
In practice, that usually means duplicated frames.

That creates a bad training pattern:

- the model sees repeated images that do not correspond to new game ticks,
- the same visual frame may appear more than once in the dataset,
- an action chunk can look like "nothing changed" even though time advanced,
- the mapping becomes noisier because frame identity no longer means unique game state.

So if the game is truly capped at 25 fps, recording at 25 fps is the cleaner choice.

### The new time math

At 25 fps:

- one frame lasts 40 ms,
- 5 frames cover 200 ms,
- one second contains 25 unique visual states.

That lines up neatly with a 200 ms action window.
If the pipeline uses `--action-window-ms 200 --action-chunks 5`, then each chunk is exactly 40 ms:

| Quantity | Value |
| --- | --- |
| Frame interval | 40 ms |
| Action window | 200 ms |
| Chunks per window | 5 |
| Chunk duration | 40 ms |

This is the cleanest alignment we have discussed so far because the visual cadence and the control cadence both become integer-friendly.

### Why this is better than 30 fps for a 25 fps game

If we keep recording at 30 fps, the 200 ms window still covers 6 capture frames, but one of those frames is often synthetic duplication rather than a new game state.
If we instead record at 25 fps, the 200 ms window covers exactly 5 unique frames.

That gives us:

- no forced duplication from the recorder,
- cleaner frame-to-state correspondence,
- a natural 40 ms chunk size,
- simpler reasoning about what the model is predicting.

### What this means for our pipeline

If your current game really stays at 25 fps, then the most coherent setup is:

- Game: 25 fps,
- Video capture: 25 fps,
- Input logger: 10 ms polling,
- Action window: 200 ms,
- Action chunks: 5,
- Chunk duration: 40 ms.

That is a better fit for the game than the earlier 30 fps or 60 fps assumptions.
It keeps the recording side aligned with the actual rendered frames while still preserving the high-resolution input truth from the 10 ms logger.

### Relationship to Lumine

This is still not the same as Lumine, but it borrows the important idea correctly:

- a fixed observation period,
- a fixed chunked action horizon,
- high-frequency input logging underneath,
- direct tokenizable action serialization.

The difference is that our natural cadence becomes 25 fps / 200 ms / 5 chunks instead of 60 fps / 200 ms / 6 chunks.
For a 25 fps game, that is the more principled mapping.

## What Changes If The Game Is Actually 60 FPS

Since the game is now running at 60 fps, the cleanest recording-side recommendation changes again.

### New time math

At 60 fps:

- one frame lasts 16.667 ms,
- 6 frames cover 100 ms,
- 12 frames cover 200 ms,
- the visual stream is twice as dense as 30 fps and three times as dense as 25 fps.

That means a 200 ms Lumine-style action horizon now spans 12 rendered frames instead of 6.

### What this means for our setup

If the capture truly stays at 60 fps, then recording at 60 fps is the correct choice.
There is no duplicate-frame problem from the capture layer as long as the recorder keeps up with the game.

The practical implications are:

- 60 fps recording preserves every unique game tick,
- the 10 ms input logger remains fine,
- a 200 ms action window is still usable,
- but that 200 ms window now covers 12 frames, so a frame-by-frame export will be much more redundant than before.

### Best interpretation

For a 60 fps game, the choice is not "should we capture at 60 fps?" The answer is yes.

The real design choice is whether we want:

1. a frame-level dataset with a short action window, or
2. a Lumine-style observation/action separation where observations are sampled more sparsely and the action horizon stays at 200 ms.

If the goal is to stay close to Lumine's logic, 60 fps recording is now the right foundation, because it lets us preserve all motion detail and then decide later how aggressively to downsample observations.

So the current state is:

- 60 fps game,
- 60 fps capture,
- 10 ms input polling,
- the mapping policy can now be chosen deliberately instead of being forced by a lower render rate.

## Bottom Line

Lumine is the better reference if the question is, "What is the most faithful high-fidelity imitation-learning recipe?"

Our current pipeline is the better choice if the question is, "What can we reliably record, align, inspect, and train from right now on this machine?"

The current design is therefore a practical compromise:

- closer to Lumine in logging structure than the original naive mapper,
- but intentionally less aggressive in windowing and scene modeling,
- with defaults chosen to avoid overlapping labels on 30 fps data.

## Final Gemma 4 E4B Pipeline

This is the pipeline we are committing to now for Gemma 4 E4B.

| Component | Final choice |
| --- | --- |
| Game FPS | 60 FPS |
| Frame limiter | Off |
| Video capture FPS | 60 FPS |
| Resolution | 1024 x 768 |
| Window mode | DxWnd windowed |
| Input logger polling | 10 ms |
| Action window | 200 ms |
| Action chunks | 6 |

### What this means operationally

- The game and the capture stream now run at the same 60 fps cadence, so each captured frame corresponds to a unique rendered game frame rather than a recorder-generated duplicate.
- The 10 ms logger stays as the high-resolution truth layer underneath the video stream.
- The 200 ms action window with 6 chunks gives us the Lumine-style future control horizon while keeping the control text chunked and tokenizable.
- The 1024 x 768 DxWnd window is the fixed visual input size we will train around.

### Why this is the right compromise

This setup keeps the parts of Lumine that matter most for control quality:

- synchronized video and input streams,
- high-frequency input logging,
- chunked action prediction over a fixed temporal horizon,
- tokenized action text rather than a continuous control head.

At the same time, it stays realistic for our local GTA SA setup because we are not changing the game resolution again and we are not trying to force scene-aware mouse switching before we have a reliable classifier.

So the final working assumption is:

- 60 fps visual capture,
- 1024 x 768 windowed play through DxWnd,
- 10 ms raw input polling,
- 200 ms action windows split into 6 chunks,
- mapping built from `manifest.json` + `frame_timeline.jsonl` + `inputs.jsonl`.
