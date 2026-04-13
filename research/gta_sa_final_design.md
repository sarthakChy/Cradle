# GTA SA Final Design

This document consolidates the findings from the Lumine note, SIMA 2, and the GTA SA-specific experiments into one practical plan for a solo, local-first project.

## Executive Summary

The right direction is not to train a model directly from raw gameplay logs alone, and not to jump immediately to a giant end-to-end policy.

The best practical path is:
- record raw gameplay with synchronized input logs,
- convert the recordings into aligned training traces,
- train a local model on cleaned traces,
- add instruction-paired and task-paired supervision,
- and build a small self-improvement loop from successful and failed runs.

This is the combined lesson from Lumine and SIMA 2:
- Lumine contributes the control pipeline: raw pixels, timing, action chunking, and precise visuomotor execution.
- SIMA 2 contributes the assistant layer: goal following, instruction grounding, conversation, and self-improvement from tasks and rewards.

## Findings

### 1. Raw gameplay capture is the correct starting point

The attached Lumine research note supports the idea that embodied agents should be trained from synchronized video and input data. That means the source material should be:
- gameplay video,
- keyboard events,
- mouse events,
- and timestamps.

For GTA SA, this matters because the game mixes two different control regimes:
- 2D GUI states such as menus, pause screens, and dialogs,
- 3D overworld control such as movement, camera motion, driving, and combat.

### 2. Raw logs are not the final training format

Raw capture is only the collection stage. Before training, the data must be:
- aligned,
- cleaned,
- chunked,
- and represented in a stable action format.

This is where the earlier recommendation changes slightly. The correct object of training is not the raw recording itself, but the processed episode trace derived from that recording.

### 3. SIMA 2 adds the missing goal layer

SIMA 2 shows that a useful generalist embodied agent is not only a motor policy. It also needs:
- high-level goal understanding,
- instruction following,
- language-and-image grounding,
- and the ability to improve from tasks and rewards.

So the GTA SA agent should not just replay actions. It should also learn to interpret what the task is and what subskill to use next.

### 4. The strongest solo path is local-first with a small curriculum

A solo project cannot realistically reproduce the scale of Lumine or SIMA 2. That means the pipeline should be simplified:
- local runtime first,
- small skill vocabulary,
- deterministic action mapping,
- task labels that are easy to score,
- and incremental improvement from runs.

### 5. Remote help is a fallback, not the default

If local training becomes too limited, the fallback should be:
- use a larger model as a teacher for offline labeling or prompt generation,
- keep the runtime controller local,
- and do not move the live input loop off-machine unless absolutely necessary.

## What We Should Make

The project should be treated as a layered agent system, not a single monolithic model.

### Layer A: Perception
- Read the screen.
- Detect UI state versus 3D gameplay.
- Extract OCR and visual cues.
- Compress the current state into a short summary.

### Layer B: Mode Routing
- Classify the current state into a mode such as menu, on-foot, vehicle, combat, navigation, or recovery.
- Decide whether the agent needs reasoning or can execute a routine skill.

### Layer C: Skill Policy
- Map the selected mode and task into a small action vocabulary.
- Use stable skills for movement, camera, interaction, and combat.
- Keep the action space narrow and deterministic.

### Layer D: Execution
- Send the chosen keyboard and mouse actions.
- Re-focus the window if needed.
- Retry safely on failure states.

### Layer E: Memory
- Store short-term observations for the current task.
- Preserve successful traces, failure traces, and recovery traces.
- Keep a compact mission summary across turns.

### Layer F: Self-Improvement
- Generate small GTA SA practice tasks.
- Run the agent on them.
- Score the outcome.
- Add the best traces back into the training set.

## Final Recommendation on Training

The training pipeline should be staged.

### Stage 1: Base control pretraining

Use raw gameplay plus synchronized inputs to teach the model basic visuomotor control.

### Stage 2: Trace cleaning

Convert raw captures into aligned, chunked samples with:
- a short visual history,
- the current state label,
- recent action history,
- and the next action chunk.

### Stage 3: Instruction tuning

Add task text and goal labels so the model learns to connect language to action.

### Stage 4: Local self-improvement

Use short GTA SA tasks and automatic checks to generate more training examples.

## Data Pipeline

The data pipeline should follow the same logical order every time.

1. Record gameplay at a stable resolution and frame rate.
2. Log keyboard and mouse events with timestamps.
3. Separate absolute GUI mouse use from relative 3D camera motion.
4. Align the first meaningful input with the first usable video frame.
5. Remove idle segments and accidental noise.
6. Chunk the actions into a small token vocabulary.
7. Label the state as GUI, on-foot, vehicle, combat, or recovery.
8. Save the episode as a training sample.
9. Reuse successful runs as positive traces and failed runs as recovery examples.

## Architecture of the Model

This is the architecture I would recommend for the GTA SA agent.

### 1. Visual Encoder

Input:
- current frame,
- short frame history,
- optional OCR text.

Purpose:
- understand the visual state,
- detect UI elements,
- and produce a compact latent representation.

### 2. State Compressor

Input:
- visual latent,
- OCR,
- previous state summary,
- recent actions.

Purpose:
- turn the current observation into a small state vector or text summary,
- identify the current mode,
- track what has already been tried.

### 3. Mode Router

Input:
- state summary,
- task description,
- recent outcome history.

Purpose:
- select one mode from a small set:
  - menu,
  - on-foot,
  - vehicle,
  - combat,
  - navigation,
  - recovery.

### 4. Reasoning Head

Input:
- task text,
- state summary,
- mode.

Purpose:
- decide the next subgoal,
- choose whether a skill action is enough,
- or request a more deliberate plan.

### 5. Skill Policy

Input:
- mode,
- state summary,
- subgoal.

Purpose:
- output a small action plan from the registered GTA SA skills.

### 6. Action Executor

Input:
- skill actions,
- current focus/window state.

Purpose:
- send keyboard and mouse inputs to the game reliably.

### 7. Memory Module

Input:
- recent states,
- actions,
- outcomes.

Purpose:
- keep short-term mission memory,
- store reusable traces,
- and accumulate evidence for failure recovery.

### 8. Self-Improvement Loop

Input:
- successful traces,
- near-miss traces,
- failure traces,
- generated practice tasks.

Purpose:
- update the dataset,
- improve prompts,
- refine the mode router,
- and later fine-tune adapters or a small policy.

## How Lumine and SIMA 2 Map to This Architecture

### Lumine contributes
- perception cadence,
- action cadence,
- action chunking,
- and precise low-level control.

### SIMA 2 contributes
- high-level goal following,
- instruction grounding,
- task generation,
- and self-improvement from rewards.

### Combined result

The model should behave like a goal-aware controller with a fast motor layer:
- the fast layer handles repeated mechanics,
- the reasoning layer handles task selection and recovery,
- the memory layer preserves continuity,
- and the data pipeline keeps improving the agent from local runs.

## What to Build Next

### Step 1: Freeze the data format

Define the exact episode schema for GTA SA.

### Step 2: Build the recorder

Capture video, key states, mouse states, timestamps, and task labels.

### Step 3: Build the converter

Turn recordings into aligned, chunked training samples.

### Step 4: Build the router

Classify menu, on-foot, vehicle, combat, and recovery states.

### Step 5: Build the first local policy

Train only movement, UI navigation, and basic interaction first.

### Step 6: Add instruction tuning

Teach the agent to connect natural language tasks to the correct skills.

### Step 7: Add the self-improvement loop

Generate tasks, score them, keep successful traces, and retrain.

## What Not to Do First

- Do not start by training a giant end-to-end model from scratch.
- Do not rely on raw logs without cleaning and alignment.
- Do not expand the action space before the baseline works.
- Do not make remote inference the default runtime path.

## Local-First Decision Rule

Use local-only training if possible.

If local compute is not enough, reduce scope in this order:
1. shrink the prompt,
2. shrink the action vocabulary,
3. freeze the base model and train only adapters,
4. use a teacher model offline,
5. keep the live controller local.

## Conclusion

The final plan is a hybrid of Lumine and SIMA 2:
- Lumine gives the control recipe.
- SIMA 2 gives the goal and self-improvement recipe.

For GTA SA and a solo local project, the right architecture is a layered agent with a clean dataset pipeline, a small mode router, a stable skill executor, and a self-improvement loop.

That is the most realistic way to move from gameplay logging to a useful embodied agent.
