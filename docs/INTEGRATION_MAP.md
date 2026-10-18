# KAIRO integration map

2026-09-20. Authority: the reconciled `D:/KAIRO/docs/UPSTREAM_AUDIT.md`, including its preserved ten-source matrix. Inputs are the two uploaded archives, inspected without modifying them. The existing independent KAIRO runtime is retained; neither historical YORU nor Mark-LIV code is a foundation.

## Decisions before implementation

| Source | Permitted treatment | KAIRO destination and acceptance |
| --- | --- | --- |
| OpenJarvis | Apache-2.0; independently implement patterns | `runtime`, `inference`, `tools`, `authority`, `journal`, `mcp_link`: bounded loop, provider contract, typed tools, explicit grants, persistent facts; verify denial/cancellation and protocol handshake |
| Handy | MIT; independently implement capture lifecycle | `voice`: explicit microphone activation/release, stop, no listening during playback; local neural STT remains a separate adapter requirement |
| OmniVoice (k2-fsa) | Apache-2.0; isolated optional adapter | replaceable speech output contract; do not bundle weights or enable voice cloning without consent; model-backed sidecar is not yet delivered |
| jdrurka/jarvis-demo | Reference only | AURORA inspection -> exact edit -> approved command -> evidence; never equate an edit with a verified build |
| Sagar ULTRON | MIT source adaptation | `ui/lib/orbScene.ts`, hand tracking and visual CSS, with original license preserved. User's explicit UI replacement supersedes the older *visual identity* decision to use inspiration only; audit's license summary explicitly permits incorporation. New application controls and authenticated bridge are KAIRO-owned |
| agency-agents | MIT; independently implement role patterns | bounded read-only research specialist, no authority escalation; do not claim the full persona library was imported |
| vierisid/jarvis | Restricted; reference only | independent approval and observable action boundaries; no copied daemon, sidecar, telemetry, OCR or surveillance |
| FRIDAY | User-reported permission; no repository license | independently implemented MCP/voice separation; no FRIDAY code redistributed, no MIT claim |
| Previous YORU prototype | Reimplement only | retain independent KAIRO path jail, stale-hash checks, checkpoints, sticky denial, explicit memories and provider secret hygiene |
| Mark-LIV | CC BY-NC; reimplement only | behavioral reference for conversation, voice controls, tool visibility, confirmation, memory inspection, continuity and undo; do not copy Python, prompts, avatar, icons or assets |

## Interface boundary

The ULTRON renderer remains a presentation component. KAIRO owns an authenticated loopback HTTP bridge with a random process-lifetime credential, exact Host/Origin validation, bounded JSON requests, event replay and explicit UI approval decisions. The static frontend and API share one origin. No provider secrets enter the browser. UI events feed the existing application on one asyncio loop. A disconnect must not grant approval; reconnect reconstructs pending review and recent events. Stop cancels runtime, voice and pending approvals. Gesture input only rotates/zooms the scene and cannot execute tools.

Visual direction: original black `#000000`, amber `#ffaa30`, warm highlight `#ffcc66`, cream text `#fff0d4`, red errors `#ff5533`; retain the donor's monospace HUD and central layered orb. A compact conversation panel carries real transcripts, evidence and controls. Approvals show exact prepared details and independent allow/deny buttons. Reduce motion when requested; keep controls usable if WebGL fails.

## Baseline parity and rejected paths

Mark-LIV is the behavioral target, not a claim that its entire product is already reproduced. Implement and test the connected conversation/voice/tool/approval/memory/provider/cancellation surface first. Track remaining parity explicitly in STATUS.md: Gemini Live streaming/resumption, acoustic echo classification, wake word, audio-device probing, desktop/browser action families, reminders/proactive monitors and phone pairing need independent implementations and hardware/provider validation. Do not expose simulated working controls for absent capabilities.

Reject Mark-LIV's unused `core/stt.py`, `core/tts.py`, `core/llm_client.py`, installer and setup paths as implementation donors; hardcoded Gemini-only routing; plaintext model keys; unbounded tool execution; copied restricted source; stale wake-word toggles; fabricated waveform telemetry; unverified build success. The human avatar/visemes are intentionally replaced by the requested orb.

## Validation plan

Run existing KAIRO tests, add real HTTP origin/authentication/approval/event tests, test rollback against stale content, compile TypeScript and produce a static production build, inspect the rendered surface where available, and verify donor archive hashes remain unchanged. Hardware and live-provider checks are reported separately from automated tests.
