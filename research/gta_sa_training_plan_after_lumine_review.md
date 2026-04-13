# GTA SA Training Plan After Reviewing the Lumine Note

This note updates the earlier recommendation after reading the attached Lumine research summary in [lumine_research.md](lumine_research.md).

## Short answer

Yes, the previous suggestion changes.

The earlier advice leaned toward turning gameplay into structured traces first and training on those traces. The Lumine note makes it clear that the more faithful starting point is to record raw gameplay with synchronized input logs, then convert that into model-ready samples through alignment, chunking, filtration, and discretization.

So the revised answer is:
- Record raw gameplay.
- Log keyboard and mouse input at high resolution.
- Align video and input streams.
- Convert them into structured action chunks.
- Train or fine-tune on the processed traces, not on raw recordings alone.

## Why the recommendation changes

The attached Lumine note emphasizes a few points that matter for GTA SA:

1. Raw visual capture plus input logging is the correct foundation for visuomotor learning.
2. The dataset must preserve timing, action holds, relative mouse motion, and GUI versus 3D state.
3. Training directly from unstructured logs is not enough; the logs must be normalized into a clean action representation.
4. A local solo setup should keep the pipeline simple and deterministic rather than trying to mimic a large-scale research stack exactly.

That means the earlier idea was directionally correct about using logs, but incomplete about how the data should be represented before training.

## What to do for GTA SA

### Phase 1: Record the right raw data

Capture each run with:
- Video at a stable resolution and frame rate.
- Keyboard press and release events.
- Mouse movement as absolute position for menus and relative deltas for 3D camera control.
- Timestamps for every event.
- A short textual note for the task goal and the observed outcome.

For GTA SA, this is especially important because the game mixes:
- 2D UI states like pause menus, map screens, and dialogs.
- 3D overworld control with camera movement.
- Different input semantics for movement, combat, driving, and menu navigation.

### Phase 2: Normalize the raw capture

Before training, convert the recordings into a consistent structure:
- Align the first video frame with the first meaningful input timestamp.
- Separate GUI state from 3D state.
- Convert keyboard state into held/released chunks.
- Quantize mouse motion into a small action vocabulary.
- Remove idle stretches and accidental noise.

### Phase 3: Build training samples

Each sample should ideally contain:
- A short visual history.
- The current GTA SA state label.
- The recent input history.
- The next action or action chunk.
- Optional task text if you want instruction following.

This is the point where the data becomes useful for behavior cloning or fine-tuning.

### Phase 4: Train locally first

For a solo project, do not start with large-scale pretraining.
Instead:
- Fine-tune a smaller local policy or multimodal model first.
- Use your own runs as the dataset.
- Keep the action vocabulary small and deterministic.
- Add more data only after the pipeline is stable.

If Gemma 4 is strong enough in your local stack, use it as the teacher or the reasoning layer first, not necessarily as the first model to learn raw control from scratch.

## Updated view on the earlier suggestion

The earlier suggestion was:
- Use structured traces.
- Train on aligned observation/action pairs.
- Keep the system local-first.

That still stands, but it needs a correction:

- The source of truth should be raw recorded gameplay with input logs.
- The structured traces should be a processed version of that raw data.
- Training should happen after conversion into stable chunks and normalized action text.

So the new recommendation is not a rejection of the old one. It is a refinement.

## Best practical pipeline for a solo GTA SA setup

1. Record raw gameplay sessions.
2. Log inputs with precise timestamps.
3. Tag each session with the task being attempted.
4. Post-process into aligned frame-action pairs.
5. Filter idle/noisy segments.
6. Chunk actions into a compact token format.
7. Fine-tune locally on the cleaned dataset.
8. Use failures to improve the task router and prompt format.

## What I would not do first

- I would not try to train a huge end-to-end model from scratch.
- I would not depend on internet-video style pseudo-labeling first.
- I would not make the model learn from raw logs without a cleaning step.
- I would not expand the action space before the baseline works.

## If local compute is limited

If local training becomes too heavy, keep the pipeline but reduce scope:
- Train only the state router.
- Train only a small action policy for menus and movement.
- Keep the main reasoning model frozen.
- Use remote help only for offline labeling or dataset review, not for live control.

## Recommendation for the next implementation step

The next useful artifact is a dataset-spec document for GTA SA that defines:
- What to record.
- How to align the streams.
- How to represent mouse and keyboard actions.
- How to label GUI versus 3D states.
- How to turn a run into a training sample.

That would make the training plan concrete enough to implement.
