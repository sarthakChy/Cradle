# GTA SA Dataset Specification

This document defines the episode format for recording GTA San Andreas gameplay and converting it into training data.

It is designed for a solo, local-first workflow and follows the combined lessons from Lumine and SIMA 2:
- Lumine informs the raw gameplay capture and action chunking.
- SIMA 2 informs the task/instruction layer and self-improvement loop.

## Goal

Create a dataset that can support:
- base visuomotor control,
- instruction following,
- GTA SA state routing,
- and later local fine-tuning or adapter training.

The dataset must be built from raw recordings and then converted into aligned, cleaned samples.

## Recording Inputs

Each run should record:
- video frames,
- keyboard down/up events,
- mouse movement,
- mouse button events,
- timestamps,
- task text,
- outcome label.

## Core Design Rules

### 1. Keep the raw data raw

Do not label every frame manually during recording.
Capture the run first, then process it later.

### 2. Preserve timing

Every event must have a timestamp.
The dataset is only useful if video and input can be aligned accurately.

### 3. Separate GUI and 3D states

GTA SA uses different mouse semantics in menus and overworld gameplay.
The dataset must distinguish between:
- GUI state,
- on-foot state,
- vehicle state,
- combat state,
- recovery state.

### 4. Use a small action vocabulary

The model should learn a stable, limited set of actions.
Do not expose an unbounded action space.

## Episode Schema

Each recording session should be stored as one episode.

### Recommended structure

```json
{
  "episode_id": "string",
  "game": "GTA San Andreas",
  "task_text": "string",
  "start_time": "ISO-8601 string",
  "end_time": "ISO-8601 string",
  "source_mode": "direct|dxwnd|other",
  "resolution": [1920, 1080],
  "frame_rate": 60,
  "state_sequence": [],
  "action_sequence": [],
  "outcome": "success|failure|partial",
  "notes": "string"
}
```

## State Record

Each state entry should describe the current observation at a single sampling point.

### Recommended fields

```json
{
  "timestamp": 0.0,
  "frame_index": 0,
  "mode": "menu|on_foot|vehicle|combat|navigation|recovery",
  "ui_state": "string",
  "screen_summary": "string",
  "ocr_text": "string",
  "task_summary": "string",
  "recent_action_summary": "string"
}
```

### Notes

- `mode` is the main routing label.
- `ui_state` should be specific, such as `pause_menu`, `map`, `mission_prompt`, `hud_active`, or `unknown`.
- `screen_summary` should be a short natural language description.
- `ocr_text` should contain any useful on-screen text.

## Action Record

Each action entry should represent the next action chunk to execute.

### Recommended fields

```json
{
  "timestamp": 0.0,
  "chunk_start": 0.0,
  "chunk_end": 0.2,
  "action_type": "skill|macro|noop",
  "skill_name": "string",
  "parameters": {},
  "keyboard_state": ["w", "shift"],
  "mouse_dx": 0,
  "mouse_dy": 0,
  "mouse_buttons": ["left"],
  "source_action_text": "string"
}
```

### Notes

- `chunk_start` and `chunk_end` define the action window.
- `keyboard_state` should represent held keys, not only key taps.
- `mouse_dx` and `mouse_dy` should be relative deltas for 3D control.
- `source_action_text` is the tokenized representation used for training.

## Training-Ready Action Text

Use a compact text format for supervised learning.

### Example

```text
mode=on_foot | state=roadside | action=move_forward(duration=0.5)
```

For chunked control, a more explicit format is fine:

```text
W+SHIFT | mouse_dx=24 mouse_dy=0 | next_skill=run_forward
```

The exact string format can be simplified later, but it must be consistent.

## Recommended Skill Vocabulary

The initial vocabulary should stay small.

### Movement
- move_forward
- move_backward
- move_left
- move_right
- turn_left
- turn_right
- run_forward
- jump

### Interaction
- press_key
- hold_key
- release_key
- press_keys_combined
- type_text

### Mouse
- move_mouse_to_position
- click_at_position
- double_click_at_position
- mouse_drag
- mouse_scroll_up
- mouse_scroll_down

### GTA-specific
- enter_vehicle
- attack

## Sampling Strategy

### Raw recording

- Capture at a stable frame rate.
- Log input events at high resolution.
- Keep the full session intact.

### Training sampling

- Downsample to a lower perception rate if needed.
- Build short rolling windows of state and action.
- Keep enough history to preserve motion and intent.

### Suggested windows

- perception window: short rolling history,
- action chunk: 200 ms or similar,
- state history: several recent observations.

## Processing Pipeline

1. Record the session.
2. Align input timestamps with video frames.
3. Detect and label GUI versus 3D states.
4. Convert keyboard events into held-key sequences.
5. Convert mouse motion into either absolute GUI movement or relative 3D deltas.
6. Remove idle or noisy segments.
7. Segment the run into training samples.
8. Save the cleaned episode in the training format.

## Filtering Rules

Apply these filters before training:

- Remove long idle stretches with no useful action.
- Remove corrupted sessions with missing frames or broken timestamps.
- Remove obvious misaligned recordings.
- Keep failure traces if they teach recovery.
- Keep exploratory behavior if it shows useful physics or navigation.

## Labeling Rules

### Success labels

Use simple labels such as:
- `success`
- `failure`
- `partial`

### State labels

Use simple labels such as:
- `menu`
- `on_foot`
- `vehicle`
- `combat`
- `navigation`
- `recovery`

### Task labels

Keep task labels short and reusable, such as:
- `exit_pause_menu`
- `walk_forward`
- `enter_vehicle`
- `drive_to_point`
- `attack_target`

## Storage Layout

Recommended folder layout:

```text
dataset/
  raw/
    episode_0001.mkv
    episode_0001_inputs.jsonl
  processed/
    episode_0001_clean.json
  manifests/
    train.jsonl
    val.jsonl
    test.jsonl
```

## Minimal JSONL Line Example

Each processed sample can be written as one JSONL line.

```json
{"episode_id":"episode_0001","timestamp":12.4,"mode":"on_foot","task_text":"walk to the car","screen_summary":"The character is standing on a street near a parked car.","ocr_text":"","action_text":"run_forward(duration=0.5)","outcome":"partial"}
```

## Local-First Training Use

This dataset should support three training targets:

### 1. Base policy learning

Learn how to turn screenshots and state summaries into actions.

### 2. Instruction tuning

Learn how to map short task text to the correct GTA SA subskill.

### 3. Recovery learning

Learn how to respond when the agent gets stuck or enters the wrong mode.

## Final Recommendation

If you use this spec, your workflow should be:

1. Record raw GTA SA gameplay with input logs.
2. Convert recordings into episodes matching this schema.
3. Train on the processed samples.
4. Add instruction-paired examples.
5. Add self-generated practice tasks.
6. Keep improving the dataset from successful and failed runs.

This gives you a realistic solo path that keeps the runtime local while still borrowing the best ideas from Lumine and SIMA 2.
