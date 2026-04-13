# GTA SA Training Plan After Reviewing SIMA 2

This note corrects the earlier training recommendation after checking [SIMA 2](2512.04797v1.pdf) alongside the Lumine-style dataset note in [lumine_research.md](lumine_research.md).

## Direct answer

The previous method was only partly right.

Recording gameplay with input logs is still the correct foundation, but SIMA 2 makes it clear that raw logs alone are not enough if the goal is a generalist GTA SA agent. The better plan is staged:

1. Raw gameplay capture with synchronized inputs.
2. Structured conversion into aligned visual-action traces.
3. Instruction-paired or task-paired fine-tuning.
4. Self-improvement from generated tasks and rewards.

So the training method should not be “just train on raw logs.” It should be “build a local data pipeline from raw logs, then train on cleaned traces plus instruction/task supervision.”

## What SIMA 2 changes

SIMA 2 matters because it emphasizes a different part of the problem than Lumine:

- Lumine is strongest on the visuomotor side: perception cadence, action cadence, and precise control.
- SIMA 2 is stronger on the assistant side: goal following, language grounding, conversation, and self-improvement.

That means a GTA SA agent should not only learn how to move the camera and press keys. It should also learn:
- how to interpret a mission or task goal,
- how to decide which subskill is needed,
- how to recover from failure,
- and how to improve from tasks it creates or is given.

## What the data should look like

The training set should mix three kinds of data.

### 1. Raw demonstration traces

Use these to learn base control.
- Video capture
- Keyboard down/up events
- Mouse movement and clicks
- Timestamps

This is the Lumine-like foundation.

### 2. Instruction-paired traces

Use these to teach goal following.
- Task text
- Screenshot sequence
- Input history
- Next action or action chunk
- Outcome

This is the SIMA 2-like layer.

### 3. Self-generated practice tasks

Use these to expand capability in a solo setup.
- Exit pause menu
- Walk to a point
- Enter vehicle
- Drive to a location
- Aim and shoot
- Interact with map or mission UI

These tasks should have simple success checks so you can automate scoring locally.

## Updated recommendation for GTA SA

If the project stays local and solo, the best path is:

### Stage A: Base control
- Train on synchronized gameplay and inputs.
- Keep the action vocabulary small.
- Focus on movement, camera, and UI interaction.

### Stage B: Instruction tuning
- Add short textual task prompts.
- Teach the model to choose the right skill for the current goal.
- Use GTA-specific labels such as menu navigation, on-foot movement, driving, and combat.

### Stage C: Task generation and self-improvement
- Use the model or rules to generate small new tasks.
- Score runs automatically.
- Save successful and near-successful traces.
- Re-train on the improved set.

## What I would change from the earlier suggestion

I would revise the earlier approach in three ways:

### Change 1: Do not stop at raw traces

Raw logs are the starting point, not the end product.

### Change 2: Add instruction data early

SIMA 2 suggests that a good embodied agent needs to understand goals, not just replay inputs.

### Change 3: Add a self-improvement loop

The paper’s open-ended learning angle matters more than I first emphasized. For GTA SA, a small local curriculum is more useful than one giant passive dataset.

## Why this is better for GTA SA

GTA SA has a lot of structure that a solo project can exploit:
- Menus and dialogs can be labeled automatically.
- Movement and driving can be checked with simple heuristics.
- Combat and camera control can be scripted into small tasks.
- Mission progress can often be verified from the screen state.

That makes it a good candidate for a hybrid pipeline where the same run can support both imitation learning and task-based fine-tuning.

## If local compute is limited

If full multimodal fine-tuning is too heavy locally, keep the same dataset design and reduce the training scope:
- Fine-tune only a router or planner.
- Keep the base VLM frozen.
- Train small adapters or LoRA modules.
- Use the main model as a teacher for labeling rather than as the only trainable component.

## Final answer

Yes, raw gameplay recording is the right foundation.
No, raw logging alone is not the full method.

The corrected GTA SA plan is:
- record raw gameplay and inputs,
- convert them into aligned traces,
- add instruction-paired examples,
- and use a local self-improvement curriculum.

That is the closest practical mix of Lumine and SIMA 2 for a solo local project.
