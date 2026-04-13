# GTA SA Live Test

Use the project virtual environment from the repository root.

## Recommended command

```powershell
& .\.venv\Scripts\python.exe runner.py --llmProviderConfig conf\ollama_config.json --embedProviderConfig conf\ollama_config.json --envConfig conf\env_config_gta_sa.json
```

## Optional two-step version

```powershell
.\.venv\Scripts\Activate.ps1
python runner.py --llmProviderConfig conf\ollama_config.json --embedProviderConfig conf\ollama_config.json --envConfig conf\env_config_gta_sa.json
```

## Before you run

1. Open GTA San Andreas in windowed borderless mode.
2. Make sure the window title is `GTA: San Andreas`.
3. Keep the game visible on screen before starting the runner.
4. Run the recommended command from the repo root.

Borderless mode is supported here without forcing a resize, so the runner should attach to the existing game window instead of trying to change its dimensions.

## What this does

- Starts Cradle using the local Ollama config.
- Uses the GTA San Andreas environment config.
- Forces the launch through the `.venv` interpreter so the correct dependencies are used.

## If it fails

- Recheck that the game title is exactly `GTA: San Andreas`.
- Confirm the `.venv` folder exists in the repository root.
- Verify Ollama is running and the models are available.
