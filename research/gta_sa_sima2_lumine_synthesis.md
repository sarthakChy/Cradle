# GTA SA Agent Design Synthesis: SIMA 2 + Lumine

This note is a GTA San Andreas-specific design sketch that mixes the strongest ideas from [SIMA 2](2512.04797v1.pdf) and [Lumine](2511.08892v1.pdf), while staying realistic for a solo project that must run locally first.

## Why these two papers matter

### SIMA 2
- Treats the agent as an interactive partner, not just a command executor.
- Uses language and images together for high-level reasoning.
- Supports open-ended self-improvement by generating tasks and rewards.
- Focuses on generalist behavior across many virtual worlds.

### Lumine
- Uses a human-like perception -> reasoning -> action loop.
- Runs perception at a lower frequency and actions at a higher frequency.
- Adapts reasoning only when needed, instead of thinking constantly.
- Is practical about both 3D world control and 2D UI manipulation.

## What to borrow for GTA SA

### From SIMA 2
- Goal-centric planning over brittle one-shot commands.
- A conversation-aware memory of what is happening and why.
- Self-generated practice tasks for skill growth.
- Reward or success signals that are inferred from the environment, not hand-labeled for every step.

### From Lumine
- A split between perception rate and action rate.
- A policy that can output precise low-level keyboard and mouse actions.
- Reasoning that is triggered selectively.
- A unified treatment of 3D gameplay and 2D UI interaction.

## GTA SA interpretation

GTA SA is a good fit for a hybrid of the two papers because it has:
- Free-form movement in a 3D world.
- Frequent UI interactions in pause menus, dialogs, mission screens, and map screens.
- Many repeatable subskills: movement, driving, camera control, combat, menu selection, navigation.
- A strong need for long-horizon task memory.

The best target is not a giant end-to-end model. The best target is a layered local system:

1. A local VLM for perception and short-horizon reasoning.
2. A skill layer for stable low-level actions.
3. A task layer that converts goals into subgoals.
4. A self-improvement loop that uses local traces and automatic checks.

## Proposed mix

### Core loop
- Perceive at a modest cadence, not every frame.
- Decide whether the current state needs reasoning or just skill execution.
- If the state is routine, use the skill layer directly.
- If the state is ambiguous, ask the model for a structured decision.
- Keep all actions grounded in a small, explicit GTA SA skill vocabulary.

### Memory loop
- Store short-term observations for the current mission.
- Compress repeated state into task summaries.
- Preserve failures, retries, and menu states as first-class memory.
- Track what worked in direct mode versus wrapper mode such as DXWnd.

### Self-improvement loop
- Generate small GTA SA tasks automatically.
- Use scripted success checks where possible.
- Rank traces by whether they achieved movement, menu exit, mission progress, or combat progress.
- Turn successful traces into new skill examples or prompt examples.

## Solo-project constraints

This is where the papers need to be simplified.

### What is realistic locally
- Inference with a local multimodal model.
- A small skill library.
- Rule-based reward checks for simple tasks.
- Replay of collected trajectories.
- Light fine-tuning or adapter training if the model and GPU allow it.

### What is probably not realistic locally
- Training a SIMA/Lumine-scale foundation model from scratch.
- Large-scale distributed self-play.
- Massive synthetic dataset generation at paper scale.
- Heavy online RL over many environments.

### Practical compromise
- Keep runtime fully local.
- Use a remote model only if necessary for offline task generation or labeling.
- Treat any remote usage as a teacher, not the deployed controller.

## GTA SA design recommendation

The strongest local-first design is a three-layer stack:

### Layer 1: Perception and state compression
- Screenshot OCR and visual description.
- Detection of pause menu, HUD, driving state, on-foot state, combat state, and map state.
- A concise state summary that survives across turns.

### Layer 2: Tactical reasoning
- Convert the current state into one of a few tactical modes.
- Examples: explore, move, enter vehicle, combat, menu navigation, recover from failure.
- Only invoke deeper reasoning when the mode is unclear or the action failed.

### Layer 3: Stable skills
- Use a narrow GTA SA skill set for movement, camera, interaction, and combat.
- Keep the skill names and control bindings deterministic.
- Avoid letting the model invent low-level actions that are not in the registry.

## Suggested research direction

If the goal is to extend Cradle for GTA SA, the best next research questions are:
- Can a local model reliably classify GTA SA state from screenshots alone?
- How small can the skill vocabulary be before the agent loses robustness?
- Can task success be checked automatically for menu navigation, movement, and mission progress?
- How much reasoning can be removed by better state compression?
- Does DXWnd require a separate action backend permanently, or only in some window modes?

## Short version

Use Lumine for the action cadence and human-like perception/action split. Use SIMA 2 for the idea of a conversational, self-improving generalist. For GTA SA, do not chase full end-to-end training first. Build a local, skill-grounded, state-aware agent with a lightweight self-improvement loop.
