# Compact UI and mobile controls

The large always-visible panel is removed. Use the small **Mobile** and **Settings** controls. See [phone setup and live screen controls](docs/MOBILE.md). The Windows wake-listener startup bug is fixed.

# KAIRO

KAIRO combines the adapted ULTRON orb with an independently implemented Gemini Live assistant and the existing KAIRO permission-scoped engineering runtime. This is an integration build; full Mark-LIV feature parity is not yet achieved. See STATUS.md for the explicit remaining work.

## Run on Windows

Requires Python 3.12 or newer. Run `Setup-KAIRO.cmd` once, then `Start-KAIRO.cmd`. The production UI is included, so Node is needed only when rebuilding it. Open the private localhost link printed by the launcher. The link contains a process-lifetime browser credential; do not share it. Close the launcher with Ctrl+C to stop the server.

Before launch, configure `GEMINI_API_KEY` or `GOOGLE_API_KEY` in the environment. Alternatively set `KAIRO_CREDENTIALS_FILE` to an absolute, private local JSON file containing the field `gemini_api_key`. Keep that file outside this project, protect it with your Windows account permissions, and never paste its contents into chat. Keys are not sent to the browser or stored in source. Google account/model access and API usage are required for a real connection.

The selected model is `models/gemini-3.1-flash-live-preview`, matching the uploaded Mark-LIV active path, with Charon voice and native audio. Settings can change provider/model/voice explicitly. KAIRO never silently substitutes a local model. Provider error messages are sanitized. Voice changes start a fresh conversation.

Talk opens the local microphone and streams mono PCM16 at 16 kHz to Gemini. Finish speaking closes input. Gemini sends audio at 24 kHz plus transcripts. Stop interrupts playback, cancels pending approvals and closes the live session. Microphone/camera are off at launch. Gestures optionally use the camera for local orb manipulation; their model/WASM resources download from Google/jsDelivr on first activation. Gestures never grant tool authority.

## What is connected

- Gemini Live conversation, streamed audio/transcripts, RAM-only resumption and bounded compatibility fallback.
- ULTRON-derived orb/drag/zoom/optional hand gestures with KAIRO identity and preserved MIT attribution.
- Typed tools, exact action review, audit, MCP allowlist, explicit memories with deletion and recall.
- AURORA path-scoped inspection, checkpointed edits, stale-content protection, undo, approved command aliases and verification evidence.
- On-demand research tools; provider-independent core contracts. Gemini Live handles research directly through those tools; the compatible-provider specialist is not silently invoked with a local model.

Configuration lives in `%APPDATA%\KAIRO\config.json` by default. Use `--data-dir PATH` to isolate another installation. Existing configurations are not silently replaced; select Gemini Live and the matching model in Settings if using an old configuration. `brain` also supports `api_version`, `api_key_env`, `credentials_file`, `proactive_audio`, `media_resolution`, `thinking_enabled`, `turn_tuning`, `input_device` and `output_device`. Advanced changes require restarting.

The optional independent OmniVoice output adapter applies only to the compatible provider: set `voice.output` to `omnivoice`, `voice.python` to an absolute Python executable with OmniVoice/sounddevice installed, `voice.model_path` to an absolute local model directory, and `voice.device` to the selected backend. It is offline, does not expose cloning, and has not been validated with model weights in this build.

## Development checks

Install pytest into the same environment and run `python -m pytest -q` from this folder. Run `python scripts/mcp_probe.py` for a real local MCP handshake. Rebuild the UI with `npm ci` then `npm run build` in `ui`. The source tree retains an optional Tk fallback via `python -m kairo desktop`.

The audit and integration map are in `docs`. Historical donor names occur there for provenance only. No donor archive is modified. No Mark-LIV/RSAL-restricted code, prompt, icon or avatar is redistributed.
# Native voice upgrade

Start with [Windows setup and native voice guide](docs/NATIVE_UPGRADE.md). Double-click `Setup-KAIRO.cmd` once, then `Start-KAIRO.cmd`. The full-panel native app is now the normal entry point. See [changelog](CHANGELOG-NATIVE.md) for changes and the guide for tested behavior and remaining limitations.

The notes below are retained from the earlier release and may describe the old browser/manual-talk workflow.
