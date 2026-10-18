# Active Gemini Live reference

Both user-supplied Mark-LIV archives have SHA-256 `5f1c4f8378cc21cc39a8fad4c0325d46bde0004a3bfdd7c3b520d9ad8ff2792c`.

Observed in `main.py:99–103`, `_build_config`, `_tuning_config`, `_receive_audio`, and the main connection loop; defaults in `memory/config_manager.py`. No restricted source or prompt is copied.

| Setting | Active upstream default | KAIRO contract |
| --- | --- | --- |
| Transport/model | google-genai Live WebSocket, `models/gemini-3.1-flash-live-preview` | Same default, configurable provider/model |
| API version | v1alpha; v1beta when enhanced config rejected | Same bounded compatibility fallback, never switch model or provider silently |
| Output | AUDIO, Charon | Same; configurable prebuilt voice |
| Transcription | Input and output enabled | Same; text is shown in the UI and not persisted as raw conversation |
| Audio | mono PCM16; 16,000 Hz input; 24,000 Hz output; capture blocks 1,024 samples | Same formats; independent capture/send/receive/playback |
| Resume | In-memory handle; accept only resumable updates | Same; do not persist handles or replay user actions after a dropped turn |
| Compression | SlidingWindow with server defaults | Same |
| Proactive audio | true | Same default |
| Turn tuning | disabled; opt-in 550 ms silence, 150 ms prefix, high end sensitivity, default start | Same configurable values |
| Media resolution | medium | Same default |
| Thinking | Omit field by default; opt-in budget -1 | Same |
| Tool execution | Function declarations and responses in live session | KAIRO tool registry with exact approval and audit; no model-issued approvals |
| Voice change | Reconnect with fresh context | Same; inform user |
| Interruption | Explicit stop; acoustic barge-in disabled | Explicit stop closes session and clears queued audio/approvals; no automatic tool replay |

Intentional compatibility differences: microphone opens only after Talk in the new UI rather than automatically at application launch; Stop discards the resumable handle so a cancelled action cannot be silently resumed; connection retries are bounded; keys remain in environment or a separate user-managed credential file, not source or browser state. The orb replaces the head and viseme renderer. A changed tool registry reconnects before the next turn. Failed in-flight turns require explicit resubmission to avoid duplicate actions.

Set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) in the launcher environment. Alternatively set `KAIRO_CREDENTIALS_FILE` to an absolute local JSON file containing `gemini_api_key`; protect this file with your Windows account permissions. KAIRO never returns its contents to the browser or logs provider exception text. An optional `brain.credentials_file` can identify that file. Do not place credential files in the project or package.
