# KAIRO status — 2026-09-20

Complete for the requested integration build.

- KAIRO identity and authenticated loopback web bridge are active.
- ULTRON orb, drag/zoom and optional hand gestures are adapted with MIT attribution.
- Gemini Live is the default brain: `models/gemini-3.1-flash-live-preview`, Charon voice, mono PCM16 16 kHz input, native 24 kHz output, input/output transcription, resumption, compression and bounded compatibility fallback.
- Mark-LIV behavior is independently reimplemented where compatible; no Mark-LIV code, prompts, avatar or restricted assets are bundled.
- KAIRO approvals, audit, memory, MCP allowlist, cancellation, checkpoint undo, stale-write protection and AURORA evidence remain active.
- 33 Python tests pass; the production UI build passes; the real local MCP probe passes; AURORA inspection remains read-only.

Live Gemini validation is pending a user-provided local `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or private `KAIRO_CREDENTIALS_FILE`. The automated Gemini tests use a protocol fixture and do not claim a live provider connection.

Remaining deliberately unclaimed parity: wake word, acoustic echo cancellation, phone dashboard, proactive scheduling/monitors, full desktop/browser action families, and hardware microphone/speaker validation. The UI does not expose simulated controls for these.
