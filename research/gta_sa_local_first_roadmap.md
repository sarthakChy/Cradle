# GTA SA Local-First Roadmap

This is a practical execution plan for a solo GTA San Andreas agent that stays local by default and only falls back to remote help if the local path proves too limited.

## Goal

Build a GTA SA agent that can:
- Understand the current game state from screenshots and OCR.
- Switch between menu handling, on-foot control, driving, and combat.
- Complete small tasks reliably.
- Improve from local traces without needing large-scale infrastructure.

## Phase 0: Lock the baseline

Before adding anything new, keep the current Cradle GTA SA path stable.

### Deliverables
- Direct local inference works.
- GTA SA config, window matching, and input routing are stable.
- The agent can enter the game, recover from pause/menu states, and move.
- Logs and screenshots are saved for every run.

### Exit criteria
- A repeatable run can be started locally.
- The agent can complete at least one very small task end-to-end.

## Phase 1: Split perception from action

This is the most Lumine-like change.

### Idea
- Perception should happen at a lower cadence.
- Skill execution should happen at a higher cadence.
- Reasoning should be triggered only when the state changes or the current plan fails.

### Implementation sketch
- Produce a compact state summary from the latest screenshot.
- Cache the summary for a few steps.
- Re-run the expensive model call only when needed.
- Keep direct skills deterministic and fast.

### Local advantage
- This reduces model calls.
- It improves latency.
- It makes local inference much more feasible.

## Phase 2: Build a GTA-specific mode router

The agent should not reason from scratch every turn.

### Suggested modes
- `menu`
- `on_foot`
- `vehicle`
- `combat`
- `navigation`
- `stuck`
- `recovery`

### Why this matters
- A mode router is cheaper than free-form planning.
- It makes prompts shorter.
- It reduces confusion between similar actions.
- It creates a natural place for heuristics.

## Phase 3: Add task scaffolding

This is the SIMA 2-inspired part.

### Goal
Teach the agent to treat tasks as things it can practice.

### Practical solo version
- Generate a small list of GTA SA tasks.
- Example task types:
  - exit the pause menu
  - walk to a marked location
  - enter a vehicle
  - drive a short route
  - aim and shoot a target
  - open map or stats and return
- Score them with simple success checks.
- Save successful traces as examples.

### Why this is enough
- You do not need a giant RL system.
- A small set of hand-made or semi-generated tasks is enough to start.
- The value is in consistency and trace quality, not scale.

## Phase 4: Self-improvement loop

This is the part to keep local-first but still useful.

### Loop
1. Generate a task.
2. Run the agent.
3. Score the run.
4. Save the trajectory if it worked or nearly worked.
5. Turn the trajectory into a better prompt, skill example, or failure note.

### What to improve first
- Menu handling.
- Camera control.
- Movement stability.
- Enter-vehicle behavior.
- Recovery from failure states.

### What not to overbuild yet
- Large-scale policy training.
- Complex reward models.
- Automatic curriculum generation across many games.

## Phase 5: Local data flywheel

The best solo setup is a small but high-quality loop.

### Data to keep
- Screenshot sequences.
- OCR text.
- Chosen mode.
- Chosen action.
- Success/failure label.
- Notes about what was wrong.

### Data to avoid
- Huge low-quality logs.
- Unlabeled runs with no outcome signal.
- Repeated failures that do not teach anything.

### Expected payoff
- Better prompt design.
- Better skill selection.
- Better failure recovery.
- Easier local fine-tuning later.

## If local compute is not enough

If a fully local model cannot handle all reasoning well enough, do not move the runtime controller off-machine immediately.

### Preferred fallback order
1. Shrink the prompt and the skill set.
2. Add stronger heuristics and mode routing.
3. Use a smaller local model for routine steps and a larger local model only for hard states.
4. Use a remote model only as a teacher for offline labeling or task generation.

### What to keep local no matter what
- Input execution.
- Screen capture.
- State memory.
- Skill dispatch.
- Final control loop.

## Concrete next experiments

1. Build a `mode_router` that classifies the current GTA SA state.
2. Add a `task_success_checker` for simple tasks like menu exit and movement.
3. Record every successful run as a reusable trace.
4. Compare direct mode and DXWnd mode separately.
5. Try a tiny curriculum: menu -> movement -> enter vehicle -> drive.

## Working assumption

The most likely winning path for a solo project is not paper-scale imitation. It is a compact local agent that borrows the structure of Lumine and SIMA 2, then uses GTA-specific skills, strict state tracking, and a small self-improvement loop.
