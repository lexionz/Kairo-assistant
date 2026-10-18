# YORU — Upstream Audit

**Date:** 2026-09-18 (updated 2026-09-18)
**Auditor:** YORU build pipeline (opencode)
**Status:** Inspection complete. No upstream repository was modified. No code was copied, merged, or ported into YORU (audit only).

## ⚠️ Architecture Rule (governing)

**YORU is a completely new project.** It must NOT use any existing implementation as a base — no forking, renaming, reskinning, or continuing of the existing **YORU/LUNARIS** prototypes, and no blind combining of upstream code.

- All upstream repositories **and the previous YORU/LUNARIS builds** are **reference/donor material only** — study them for proven solutions, failures, patterns, and legally reusable components.
- The production implementation will be created **only inside `D:\YORU\app`**, from a clean starting point, and only after this audit is complete and the user gives the go-ahead.
- YORU must have its **own** architecture, module boundaries, configuration, UI/UX, identity, permission model, tests, and documentation.
- Every borrowed component must record origin, license, and reason for inclusion. Where useful architecture is license-restricted, implement the idea independently.
- The existing YORU/LUNARIS code may be inspected to learn what worked and what failed, but it must NOT become the foundation of the new project.

---

## 1. Scope & Method

Eight repositories were cloned into `D:\YORU\upstream\`. Each was inspected recursively: README, package/pyproject manifests, lockfiles, source trees, docs, LICENSE/NOTICE files, and the key implementation files that determine architecture and reusability.

| # | Repo | Clone path | VCS |
|---|------|-----------|-----|
| 1 | `open-jarvis/OpenJarvis` | `D:\YORU\upstream\OpenJarvis` | git ✓ |
| 2 | `SAGAR-TAMANG/friday-tony-stark-demo` | `D:\YORU\upstream\friday-tony-stark-demo` | git ✓ |
| 3 | `jdrurka/jarvis-demo` | `D:\YORU\upstream\jarvis-demo` | git ✓ |
| 4 | `vierisid/jarvis` | `D:\YORU\upstream\jarvis` | git ✓ |
| 5 | `cjpais/handy` | `D:\YORU\upstream\handy` | git ✓ |
| 6 | `SAGAR-TAMANG/ultron-by-sagar-builds` | `D:\YORU\upstream\ultron-by-sagar-builds` | git ✓ |
| 7 | `msitarzewski/agency-agents` | `D:\YORU\upstream\agency-agents` | git ✓ |
| 8 | `k2-fsa/OmniVoice` | `D:\YORU\upstream\OmniVoice` | git ✓ |

### OmniVoice upstream resolution

"OmniVoice" is an ambiguous name used by several unrelated projects. The user confirmed the correct upstream is **`k2-fsa/OmniVoice`** (Apache-2.0, massively multilingual zero-shot TTS / voice-cloning model from the k2-fsa research team). The other candidates considered and rejected: `plexusone/omnivoice` (Go voice-pipeline/gateway framework) and `Chuqonu/OmniVoice` (macOS-only dictation app). No wrong project was cloned.

### Repo scale (excluding `.git`)

| Repo | Files | Lines | Size |
|------|------:|------:|-----:|
| OpenJarvis | 2,146 | ~1,016,230 | 100.6 MB |
| jarvis (vierisid) | 2,934 | ~503,146 | 22.3 MB |
| handy | 381 | ~110,046 | 7.3 MB |
| agency-agents | 362 | ~73,601 | 4.5 MB |
| jarvis-demo | 70 | ~24,184 | 1.8 MB |
| ultron-by-sagar-builds | 14 | ~23,854 | 3.1 MB |
| OmniVoice | 89 | ~20,425 | 1.3 MB |
| friday-tony-stark-demo | 19 | ~3,803 | 0.6 MB |

---

## 2. Executive synthesis

The eight projects, the user's **previous YORU prototype** (§3.9), and **Mark-LIV** (§3.10) fall into seven distinct roles for a Windows desktop AI agent:

0. **Proven pattern bank (own previous work)** — the existing YORU/LUNARIS prototype (§3.9): bounded agent loop, approval+audit gate, checkpointed verified writes, provider switching, island states, Windows SAPI voice loop, scoped AURORA harness, 10 test files. **Reference-only; must not become the new base.**
1. **Local-first agent framework** — OpenJarvis (Python, Apache-2.0). The most complete and license-clean scaffolding for an agent core. *Primary architectural donor candidate.*
2. **Always-on desktop-awareness daemon** — vierisid/jarvis (Bun/TS + Go, source-available RSALv2-based). The richest reference for continuous screen awareness, Win32 automation, multi-agent hierarchy, authority gating — but cannot be copied due to license.
3. **Voice input (STT) front end** — handy (Rust/Tauri, MIT). Best local Whisper/Parakeet + VAD + push-to-talk + reliable paste-on-Windows implementation.
4. **Voice output (TTS) model** — k2-fsa/OmniVoice (Python, Apache-2.0). State-of-the-art voice cloning/design for the assistant's spoken voice.
5. **Inspiration/demo/tooling** — friday (MCP+LiveKit voice pipeline), jarvis-demo (voice→Claude Code→build orchestration), ultron (three.js orb + MediaPipe hand gestures), agency-agents (~264 markdown personality agents + multi-tool installer).
6. **Realtime-voice agent UX reference (non-commercial only)** — **Mark-LIV** (§3.10, CC BY-NC 4.0): the most polished reference for a *live*-voice desktop companion built on a streaming model API (Gemini Live) — voice pipeline with echo tail, transcript-driven lip-sync visemes, session resumption, forged-proof confirm gate, undoable actions, drop-in tool/plugin auto-discovery, software-rendered holographic head, phone remote dashboard. **License forbids code reuse in commercial software → REIMPLEMENT/REFERENCE ONLY.**

**License-limited donors:** vierisid/jarvis is *source available*, not OSI open source; its code may not be vendored into YORU. Mark-LIV is **CC BY-NC 4.0** — its code may not be vendored at all unless YORU is strictly non-commercial. Everything else is Apache-2.0 or MIT and may be incorporated with attribution.

---

## 3. Per-project audit

---

### 3.1 OpenJarvis — `D:\YORU\upstream\OpenJarvis`

**Purpose.** A Stanford (Hazy Research / Scaling Intelligence Lab) framework for *local-first personal AI*: "Personal AI, On Personal Devices." Built around shared agent primitives, energy/latency/cost-aware evals, and a local learning loop. Combines a Python agent library with an optional Rust extension and Tauri desktop app. arXiv:2605.17172.

**Architecture.** Hybrid Python (core, `src/openjarvis/`, ~36 packages, ~149k Python lines) + Rust (PyO3 extensions under `rust/crates/`; `openjarvis_rust` is mandatory at import). Three clock modes for agents: on-demand, scheduled (croniter), continuous. Eight built-in agents registered via `core/registry.py`. Installers target macOS/Linux/WSL2 + native Windows (`.ps1`, scheduled-task service, `.exe` desktop bundle).

**Voice/STT/TTS.** Speech stack in `src/openjarvis/speech/` and `cli/_voice_chat.py`:
- STT: `faster-whisper` (local, base model) → fallback OpenAI → Deepgram (`speech/_discovery.py`).
- TTS: Kokoro (local neural, via `voice` extra), OpenAI, Cartesia.
- I/O: `speech/voice_io.py` — `record_until_silence` (16 kHz, RMS<500 silence threshold, 5 s startup, 30 s max), `play_wav`; push-to-talk loop only.
- **No wake word, no VAD-gated always-listening** in Python; frontend mic is gesture-triggered (`frontend/src/hooks/useSpeech.ts`, MediaRecorder → `transcribeAudio` REST).

**Agent architecture.** Registry-based. `agents/native_react.py` (ReAct loop w/ `skill_*`-prefixed skill tools), `agents/orchestrator.py` (function-calling + structured THOUGHT/TOOL/INPUT/FINAL), `agents/operative.py` (persistent/scheduled, max_turns 20), `agents/executor.py` (tick runner, `_MAX_RETRIES=3`, default local model `gemma4:31b`), `agents/tool_resolver.py` (capability-based tool grants). Also: mini_swe_agent, archon, deep_research, research_loop, monitor_operative, proactive_agent, native_openhands (CodeAct), and adapters that shell out to `claude_code`, `opencode`, and Claude-Code-compatible skill translation.

**Tools/MCP.** ~44 tool files under `tools/`: `browser.py` (Playwright navigation), `web_search.py`, `git_tool.py`, `shell_exec.py` (sanitized env, `requires_confirmation=True`, capability `code:execute`, 100 KB output cap, 300 s timeout), `code_interpreter.py` (pattern-blocklist against os.system/subprocess/eval/exec/open/`__import__`, subprocess timeout), Docker and WASM sandbox runners. First-class **MCP**: `src/openjarvis/mcp/` with client/server/protocol/transports (InProcess/SSE/Stdio/StreamableHTTP); `tools/mcp_adapter.py` wraps remote MCP tools as native `BaseTool`. Skills use the **agentskills.io** open standard (`SKILL.md` frontmatter, tolerant 2-pass parser), importable from Hermes Agent and OpenClaw (~13,700 skills).

**Memory.** Two tiers:
1. `memory/store.py` — `LocalFactStore` JSONL fact log, cross-process file locking, provenance trust tiers (`auto|trusted|untrusted`, quarantine), 1000-fact cap, atomic writes, dedupe; background extractor in `memory/service.py`.
2. Vector backends `tools/storage/`: FAISS, ColBERT, BM25, hybrid (RRF fusion), dense, SQLite, knowledge graph; wrapped by MCP memory tools (`memory_store/retrieve/search/index`).
Plus persona files `SOUL.md` / `MEMORY.md` / `USER.md` bootstrapped on init and injected into prompts.

**Desktop control.** **None.** No Win32/pyautogui/pynput/SendInput anywhere. The only Windows-native touch is `ctypes.windll.kernel32.GlobalMemoryStatusEx` for RAM detection. This is the widest gap versus YORU's desktop-agent goal.

**UI.** Three surfaces: (1) Tauri 2 desktop app in `frontend/src-tauri/` (React+Vite+TS components: Chat, Dashboard, Desktop, setup, Sidebar; Rust `lib.rs` ~3k lines handles Ollama sidecar, model catalog (Qwen3.5), RAM detection, global shortcut, autostart, updater); (2) FastAPI server in `server/` (REST + WebSocket bridges, SPA static hosting); (3) TUI dashboards via `textual` and `rich`-based CLI.

**Model providers.** Local engines: Ollama, vLLM, SGLang, llama.cpp, mlx-lm, LM Studio, exo, Nexa AI, Apple FM (AFM via `apple-fm-sdk`), Gemma (pygemma/ggml). Cloud: OpenAI, Anthropic, Google genai, OpenRouter, MiniMax, DeepSeek, LiteLLM (pinned `litellm==1.98.0` for security), with per-model cost tables and OpenAI→Anthropic/Google message/tool conversion.

**Security/permissions.** Strongest in the set: `security/capabilities.py` RBAC (Capability enum: `file:read/write`, `network:fetch`, `code:execute`, `memory:read/write`, `channel:send`, `tool:invoke`, `schedule:create`, `system:admin`) with per-agent grants/denies; `security/taint.py`, `ssrf.py`, `signing.py`, `severity_policy.py` (ScanFinding/ThreatLevel), `injection_scanner.py`, `data_boundary_audit.py`; confirmation store (`approval_store.py`); Docker (`sandbox/runner.py`, mount allowlist) and wasmtime (`wasm_runner.py`, fuel/256 MB mem) sandboxes.

**Dependencies.** Python ≥3.10,<3.14. Runtime extras are optional-dependency groups: `desktop` (faster-whisper, sounddevice, onnxruntime), `voice` (kokoro), `inference-*`, `memory-faiss/colbert/bm25`, `browser` (playwright), `sandbox-wasm/docker`, channel extras (telegram/discord/slack/…), `security-signing` (cryptography). Rust workspace via uv `desktop-native` group. `uv.lock` = 9,108 lines / 1.57 MB.

**Strongest components for YORU.**
- Capability-based security RBAC + tool approval + sandbox runners.
- MCP client/server layer and MCP-tool adapter (map YORU tools to the MCP ecosystem).
- Memory tier (JSONL fact store + vector backends + persona files).
- Local-first engine abstraction (Ollama/vLLM/MLX/lmstudio + cloud router with cost tables).
- Multiple ready agent loop patterns (ReAct, orchestrator function-calling, operator, CodeAct).

**Weaknesses.**
- No desktop/window automation layer (the exact thing YORU needs most) — must come from elsewhere (handy's injection, vierisid/jarvis reference, or new code).
- No wake word / continuous VAD listening in the shipped Python path.
- No NOTICE/third-party notices file; README claims TTS via Kokoro but list is model-volatile.
- 100 MB checkout (docs, assets); heavy optional extras.

**License restrictions.** Apache-2.0 — OSI-approved, permissive, commercial-friendly. Requires attribution and license inclusion; no copyleft.

**Can actual source be incorporated?** **Yes.** Apache-2.0 permits copying, modification, and redistribution with attribution. Recommended as the architectural backbone of the YORU agent core.

---

### 3.2 vierisid/jarvis — `D:\YORU\upstream\jarvis`

**Purpose.** An *always-on autonomous AI daemon* ("Just A Rather Very Intelligent System") with desktop awareness, multi-agent hierarchy, visual workflow builder, and goal pursuit. Daemon runs on a server or local machine; lightweight Go sidecars give it "eyes and hands" on any machine (including Windows via Win32 automation).

**Architecture.** Two-process split:
- **Brain**: TypeScript/Bun daemon (`@usejarvis/brain`, v0.13.7), `src/daemon/` (~93 files), module `src/daemon/index.ts`, CLI `bin/jarvis.ts`. SQLite via `bun:sqlite` (WAL). HTTP + WebSocket server on `:3142` (JWT auth), React dashboard + "pebble" ambient UI.
- **Sidecar**: Go binary (`sidecar/`, ~260 Go files), JWT-authenticated binary WebSocket RPC back to the brain. Capabilities: `terminal, filesystem, desktop, browser, clipboard, screenshot, system_info, awareness, ocr, windows, pebble, sub_pebble, file_watch, processes, notifications`.
Daemon is Unix/WSL-first; native Windows is explicitly unsupported for the daemon itself, but the sidecar has a Windows build for desktop control.

**Voice/STT/TTS.**
- Wake word: **openwakeword** (ONNX, runs in-browser via `openwakeword-wasm-browser`; models `hey_jarvis_v0.1`, silero_vad, melspectrogram, embedding_model shipped to `ui/public/`), `ui/src/hooks/useVoice.ts`, `ui/src/lib/wakeMic.ts` (raw mic, no AEC/NS/AGC).
- TTS: Edge TTS (`edge-tts-universal`) or ElevenLabs, streaming sentence-by-sentence.
- Transport: binary WebSocket carrying mic audio (WebM) and TTS audio (MP3); `audio.session_*` inline base64 frames; `src/comms/audio-transport.ts`, `ui/src/lib/RealtimeVoiceController.ts` (gpt-realtime-2, 24 kHz PCM s16 worklet, barge-in) — realtime voice path exists.
- No local STT: transcription is cloud or realtime-API based.

**Agent architecture.** `src/agents/orchestrator.ts` main loop (`MAX_TOOL_ITERATIONS = 200`), `processMessage`/`processTaskCall`; generic `sub-agent-runner.ts` (cap 100 iters, `MAX_TOOL_RESULT_CHARS = 6000`, scoped tool registry); `task-manager.ts` AgentTaskManager (async lifecycle, background sub-agents inherit the same authority engine + taint gating); `agent.ts` state machine with `AuthorityBounds` (max_authority_level, allowed/denied tools, token budget, can_spawn_children); multi-agent hierarchy (`hierarchy.ts`, `delegation.ts`, `role-discovery.ts` — 12 specialist roles under `roles/specialists/`, README's "9" is stale); conversational loop `conv/conv-orchestrator.ts`.

**Tools/MCP.** 18 built-in tools (`src/actions/tools/builtin.ts`): `run_command, read_file, write_file, list_directory, get_clipboard, set_clipboard, capture_screen, get_system_info` + ten `browser_*` (CDP-driven Chromium: navigate, snapshot, click, hover, press_key, type, screenshot, upload_file, scroll, evaluate). Desktop UI tools (`tools/desktop.ts`, 9 `desktop_*`) auto-routed to a sidecar by capability: list_windows, snapshot, click, type, press_keys, launch_app, screenshot, focus_window, find_element. Delegation (`delegate.ts`), **agent management** (`agents.ts`: manage_agents spawn/assign/status/collect/list/terminate + persistent agent registries), approval (`approval-tool.ts`), goals, skills (`run_skill/manage_skills/record_skill`), research queue, UI snapshot/act, documents, commitments. Tool registry with enum enforcement + per-call `authorityGate`. **No MCP protocol support** found for external MCP servers (toolset is internal).

**Memory.** Vault knowledge graph in SQLite (`src/vault/`): `schema.ts` (entities, facts, relationships, commitments, goals, user-profile, awareness), `extractor.ts` (LLM extraction after each response), `recall-context.ts` (limits: 12k chars, 6 entities, 18 facts, 8 per entity, 4 relationships/entity, injected into system prompt per message).

**Desktop control.** The richest in the set:
- Sidecar RPC handlers `sidecar/handlers.go`; Win32 automation via **go-ole UI Automation** (`sidecar/uia_windows.go`, `uia_actions_windows.go`, `uia_patterns_windows.go`, `uia_cache_windows.go`), `desktop_windows.go`, `win32_native_windows.go`, `mouse_hook_windows.go`; Linux X11 + macOS variants.
- Screen capture every 5–10 s; **OCR** `sidecar/ocr_windows.go` uses Windows.Media.Ocr via embedded PowerShell (README's "Tesseract.js" claim is inaccurate — Tesseract only on the Linux path; brain-side Cloud Vision escalation gated by `cloud_vision_enabled`).
- Awareness pipeline (`src/awareness/service.ts`): struggle detection, activity session inference, entity-linked context graph, proactive suggestions + overlay widget.
- Browser control via Chromium CDP (`src/actions/browser/`).
- Client launchers `src/actions/app-control/windows.ts` + `scripts/desktop.ps1`.

**UI.** React 19.2.4 + Tailwind 4.2.1 + `@xyflow/react` (workflow builder), CodeMirror 6, `socket.io`. Room/window system (`ui/src/v2/rooms/`: agents, authority, calendar, content, goals, logs, memory, settings, tasks, tools, usage, workflows, workspaces, + Answer/TaskResult). Floating-window model via `RoomDispatcher.tsx`; "pebble" ambient UI (`ui/pebble.html`) — cursor-following disc, wake-word/`Ctrl+Space` summon, sub-pebble rail for background agents. "Native windows" via voice (voice → open a room window).

**Model providers.** Multi-provider router `src/llm/manager.ts` (provider registry, `MAX_RETRIES_PER_PROVIDER=3`, 90 s request timeout), tiered routing `tiers.ts` (conversation/high/medium/low; conversation never falls up, tasks fall up via TIER_FALLBACK). Providers: Anthropic, OpenAI, Gemini, Ollama, Groq, OpenRouter, NVIDIA (`nvidia.ts`), hosted "Usejarvis AI" OmniRoute-style (`usejarvis.ts` w/ cache_control). Personality engine + role system (`roles/`, from YAML). `docs/LLM_PROVIDERS.md`.

**Security/permissions.** Best reference for enforcing runtime autonomy: `src/authority/engine.ts` — decision order: temporary grants → per-action overrides → context rules (time/tool) → numeric level → governed category; emergency state `normal|paused|killed` (pause/kill/reset); `learning.ts` consecutive-approval → auto-approve suggestions; approval delivery via WebSocket + Telegram/Discord short-id replies; `audit.ts` audit trail; `taint-gating.ts`; `tool-action-map.ts`. JWT auth (jose) by default, `insecure_open_access` opt-in for first-run onboarding; config `~/.jarvis/config.yaml`. Telemetry: **opt-out, on by default** (anon hashed hostname+username, version, install method, OS/arch; disable via `telemetry.enabled:false` / `JARVIS_TELEMETRY=0` / `DO_NOT_TRACK=1`).

**Dependencies.** Bun runtime; root `package.json` (React 19, Tailwind 4, `@xyflow/react`, onnxruntime-web, openwakeword-wasm-browser, edge-tts-universal, discord.js, jose, socket.io, nanoid, fuse.js, CodeMirror, react-markdown, yaml). Sidecar Go 1.25 (`gen2brain/malgo`, `go-ole`, `hajimehoshi/go-mp3`, `golang.org/x/sys`, `nhooyr.io/websocket`, vendored `third_party/webview_go`). Vendored **Activepieces** workflow engine (`src/workflows/activepieces/`, pinned tag 0.82.1, MIT paths only, EE excluded, CI-checked `scripts/check-no-ee-imports.ts`) — 656-piece catalog, workflow engine runs as an isolated subprocess (socket.io polling), webhook resume.

**Strongest components for YORU.** Win32 UI Automation + screen-capture + OCR-sidecar pattern; authority/approval/audit engine; multi-agent delegation with authority inheritance; wake-word (openwakeword-wasm) + streaming TTS wiring; awareness pipeline (5–10 s capture, struggle detection, proactive suggestions); workflow node editor (n8n-style). **Reference-only** — these are superb blueprints.

**Weaknesses.** License blocks reuse; Bun-only (non-node) runtime; daemon not native-Windows (WSL/Docker); no local STT; telemetry on-by-default needs opt-out handling; README overstates tool counts/OCR (actual: 18 tools, 10 browser, native per-OS OCR); large (500k lines).

**License restrictions.** **Jarvis Source Available License 2.0 (based on RSALv2), dated 2026-03-12 — NOT OSI-approved, NOT open source.** Read `LICENSE` and `THIRD_PARTY_NOTICES.md` before any extraction. Third-party components retain their own licenses if extracted standalone. Distinguishing features available-only restrictions prevent derivative redistribution as a competing hosted service; the exact grant is proprietary.

**Can actual source be incorporated?** **No** — not into YORU's codebase as a whole. Study as a reference architecture / pattern source only. Re-implement patterns from scratch.

---

### 3.3 cjpais / handy — `D:\YORU\upstream\handy`

**Purpose.** A free, open-source, cross-platform (Windows/macOS/Linux) *speech-to-text* desktop app that works fully offline: hold a global shortcut, speak, get transcript typed/pasted into any text field. "Trying to be the most forkable STT app."

**Architecture.** Tauri 2 desktop app: React + TypeScript frontend (Tailwind, Zustand, i18next), Rust backend (`src-tauri/src/`). Manager pattern (`managers/{audio,transcription,model,history}.rs`) + command/event architecture + specta type bindings. Single-instance with CLI remote control (second instance sends args to running instance via `tauri-plugin-single-instance`).

**Voice/STT/TTS.** STT only (no TTS, no agent):
- Capture: `cpal` → lock-free `rtrb` SPSC ring (2 s) → 16 kHz mono → `rubato` resampler for non-default devices (`audio_toolkit/audio/`).
- VAD: `SileroVad` (vad-rs, 30 ms frames) + experimental `EarshotVad` (`audio_toolkit/vad/`); timing constants 450 ms prefill / 60 ms onset / 450–1650 ms hangover.
- Transcription: **transcribe-cpp** (GGML/GGUF Whisper-family: Voxrtal, Canary, Cohere, Nemotron, Parakeet… with GPU acceleration — Vulkan on Windows x64) **and** **transcribe-rs** (ONNX: Parakeet, Moonshine, SenseVoice, GigaAM; CPU-only on Windows). Model catalog `catalog.json` with pinned HF revisions + sha256; local model auto-discovery; custom GGML/GGUF supported.
- Post-processing: optional LLM cleanup pass (OpenAI / Z.AI / OpenRouter / Anthropic / Groq / Cerebras / Bedrock-Mantle / custom, local `:11434`), language detection (`whatlang`/`isolang`), filler-word removal (strsim word correction), OPENCC text conversion.
- **No wake word, no LLM agent loop** — strict mic → VAD → STT → type pipeline.

**Agent architecture.** None (not an agent). The relevant seam is `send_transcription_input()` (`signal_handle.rs`) + the "reliable paste" subsystem both for automation.

**Tools/MCP.** None. It is an input driver, not a tool platform.

**Memory.** Transcription history (`managers/history.rs`, SQLite via rusqlite + migrations); settings store (`tauri-plugin-store`, single `AppSettings` struct, versioned migrations, salvage of invalid fields, portable mode).

**Desktop control (Windows).** Strong text-injection machinery:
- `clipboard.rs` copy + `enigo` keystroke typing; paste with configurable before/after delays.
- **Reliable Paste** (Windows): `SetClipboardData(CF_UNICODETEXT, NULL)` delayed rendering + `WM_RENDERFORMAT` receipt + hidden message-only window/worker thread; wireless clipboard-restore ordering.
- Global shortcuts via `handy-keys` (rdev fork) hotkey manager on dedicated thread + `tauri-plugin-global-shortcut`; overlay window (GTK layer shell on Linux); tray; autostart; **registry mic-permission probe** via `CapabilityAccessManager` ConsentStore.
- Windows hardening: disables Vulkan implicit layers (`VK_LOADER_LAYERS_DISABLE=~implicit~`) to prevent overlay/capture-crash; `IsWow64Process2` x64-emulation detection; webview2-com accelerator disabling; NSIS signed installer via Azure trusted-signing; `tao` pinned to cjpais fork for `WM_QUERYENDSESSION`.

**UI.** Settings UI (React 18, Tailwind 4, i18next w/ many locales, sonner toasts, react-select), recording overlay, onboarding flow, model selector, update checker. Desktop-tray app with `--start-hidden --no-tray --debug` flags.

**Model providers.** STT: local Whisper GGML and ONNX Parakeet et al. LLM (only for transcript post-processing): configurable OpenAI-compatible endpoints incl. local Ollama; Apple Intelligence on macOS ARM only.

**Security/permissions.** Privacy-first: everything local; mic + accessibility OS permissions handled in onboarding; clipboard content restored after typing; no analytics by default (opt-in analytics planned); Vulkan-layer disabling to avoid third-party hooks reading the process; "reliable paste" receipts avoid leaking clipboard content to the wrong window.

**Dependencies.** Cargo: Tauri 2.11.5 + plugins (log/opener/store/os/clipboard-manager/macos-permissions/process/fs/dialog/autostart/global-shortcut/single-instance/updater), `rdev`, `handy-keys 0.3.4`, `cpal 0.16`, `rtrb`, `vad-rs`, `earshot`, `rodio` (fork), `transcribe-cpp 0.2.3`, `transcribe-rs 0.3.8`, `hf-hub`, `rusqlite` (bundled), `rubato`, `hound`, `reqwest`, `windows 0.61.3`, `webview2-com`, `winreg`, `ferrous-opencc`, `clap`, `specta`/`tauri-specta`, `tokio`; release profile LTO. Frontend: React 18, Vite 6, Tailwind 4, i18next, Zustand, immer, zod.

**Strongest components for YORU.** Production-grade local STT pipeline (Whisper GGML + Parakeet ONNX, Silero VAD, audio device handling) proven on Windows; **Reliable Paste** and clipboard/type-injection for hands-free text entry; global-hotkey infrastructure; single-instance CLI remote control (`--toggle-transcription`, `--transcribe-file --json`) ideal for an agent to invoke; model download management with pinned hashes; i18n setup.

**Weaknesses.** No agent loop, no TTS, no wake word, no LLM integration beyond transcript post-processing; Windows ARM CPU-only; updater/signing tied to Handy's infra; project is under feature freeze upstream; separate branding required (name/logo not open).

**License restrictions.** MIT (C) 2025 CJ Pais. **Brand caveat:** the Handy *name, logo, icon, and brand assets are not open source*; forks must rebrand and not imply endorsement.

**Can actual source be incorporated?** **Yes** (MIT), with attribution and independent branding. The Rust STT/VAD/audio/injection crates and architecture are directly forkable for YORU's voice-input and text-injection layers.

---

### 3.4 k2-fsa/OmniVoice — `D:\YORU\upstream\OmniVoice`

**Purpose.** A state-of-the-art massively multilingual (600+ languages) **zero-shot text-to-speech** system supporting voice cloning (from a short reference clip) and voice design (from text-described attributes). Diffusion language model TTS, k2-fsa research team. arXiv:2604.00688.

**Architecture.** Python package `omnivoice` v0.2.1. Diffusion-LM (DiT-style masked-diffusion TTS):
- **Backbone/LLM**: `Qwen/Qwen3-0.6B` (masked-diffusion transformer attending to text + discretized audio tokens, non-causal).
- **Audio codec**: `HiggsAudioV2TokenizerModel` — 8 RVQ codebooks, vocab 1025 (mask id 1024), ~22.7 Hz frame rate, 24 kHz output. Tokenizer bundled in model checkpoint.
- **Heads**: `audio_embeddings` (Embedding 1025*8) + `audio_heads` (bias-free Linear 1025*8) predicting masked audio tokens for all codebooks in parallel; per-codebook loss weights `[8,8,6,6,4,4,2,2]`.
- Generation: N diffusion iteration (default 32, or 16), classifier-free guidance (default scale 2.0), Gumbel sampling, position temperature 5.0, `t_shift` 0.1, optional `<|denoise|>` prompt mode, long-form audio chunking + crossfade to hold VRAM flat.
- `VoiceClonePrompt.save()/load()` — encode a reference voice once, reuse without ASR.

**Voice/STT/TTS.** **TTS-only**; the only ASR is the internal Whisper auto-transcription for cloning references:
- `load_asr_model()` builds an HF `pipeline("automatic-speech-recognition")`, default `openai/whisper-large-v3-turbo`, fp16 on cuda/xpu else fp32; `asr_model_name`/`asr_device` configurable (multi-GPU pinning, MPS not supported by Higgs tokenizer).
- Generation modes: (1) **Voice cloning** `ref_audio`(+`ref_text`) or prebuilt prompt; (2) **Voice design** `instruct` string (gender, age, pitch, style e.g. whisper, English accent, Chinese dialect — `utils/voice_design.py`, EN/ZH trained only); (3) **Auto voice** (text only).
- Non-verbal tags (`[laughter]`, …) and pronunciation control (pinyin tone markers, CMU dictionary brackets).
- **No streaming API** — one-shot / chunked-batch generation.

**Agent architecture.** None (model library). Architectural analog to an "engine" plugin.

**Tools/MCP.** None. CLIs: `omnivoice-infer` (single), `omnivoice-infer-batch` (multi-GPU JSONL, `ProcessPoolExecutor` spawn, FlashInfer), `omnivoice-demo` (Gradio web UI, voice-clone + voice-design tabs, 646-language dropdown), `omnivoice-merge-lora`.

**Memory.** None (not an agent). Cross-session state via saved `VoiceClonePrompt` objects.

**Desktop control.** None (headless inference).

**UI.** Gradio web demo (`omnivoice-demo --ip 0.0.0.0 --port 8001`).

**Model providers.** Self-hosted: the OmniVoice model itself on CUDA / XPU (Intel Arc, tested A310 4 GB, Arc Pro B50 16 GB) / MPS / CPU (slow). FlashInfer kernels (NVIDIA) give ~2–2.9× lossless speedup (CUDA graphs for batch=1). Whisper-large-v3-turbo ASR for reference transcription.

**Security/permissions.** Model-card disclaimer in README: **strictly prohibits unauthorized voice cloning, impersonation, fraud, scams or illegal use**; devs disclaim liability. No code-level permission system.

**Dependencies.** `torch>=2.4`, `torchaudio>=2.4`, `transformers>=5.3`, `accelerate`, `pydub`, `gradio`, `tensorboardX`, `webdataset`, `numpy`, `soundfile`, `librosa`; extras `tn` (WeTextProcessing), `eval`, `lora` (peft). uv-managed with `pytorch-cuda` (cu128) index for linux/win32. Params: ~632M total (0.6B backbone + codec heads); fp16 ≈ 1.3 GB + Higgs tokenizer + optional Whisper ASR.

**Strongest components for YORU.** Best-in-class zero-shot voice cloning and voice design behind a clean Python API; small model for the capability (~1.3 GB fp16) so a mid-range NVIDIA/Intel-GPU desktop can run it; `VoiceClonePrompt` persistence gives YORU a *stable, locally owned assistant voice* without re-running ASR each boot; voice-design (`instruct`) lets users synthesize a bespoke assistant voice with no reference audio; Windows/CUDA supported (`spawn` multiprocessing, win32 wheel markers); RTF as low as 0.025.

**Weaknesses.** Requires a discrete GPU for responsive use (iterative 16–32 diffusion passes × CFG 2×); FlashInfer gains are NVIDIA/Linux-oriented; no streaming/low-latency interjection; heavy dependency stack (torch + transformers 5.x); Whisper ASR adds startup weight (mitigable by precomputed voice prompts); ethics/liability surface around cloning — YORU should only ever clone the end-user's own voice with consent, never third parties.

**License restrictions.** Apache-2.0. Model-card usage disclaimer (no unauthorized cloning/impersonation/fraud). Voice-cloning model usage must comply with applicable law and require consent; this is a *usage* restriction carried into the incorporated component.

**Can actual source be incorporated?** **Yes** (Apache-2.0), as YORU's TTS/voice-cloning engine (subprocess/Python sidecar recommended to keep it isolated from the main YORU process).

---

### 3.5 SAGAR-TAMANG/friday-tony-stark-demo — `D:\YORU\upstream\friday-tony-stark-demo`

**Purpose.** A Tony Stark–style voice assistant demo ("F.R.I.D.A.Y.") split into an **MCP server** (FastMCP over SSE, "backend" doing real work) and a **LiveKit voice agent** (real-time STT→LLM→TTS pipeline). Showcase for wiring a voice pipeline to MCP tools in real time.

**Architecture.** Two Python processes (uv-managed, hatchling):
- `server.py` → `friday`: FastMCP SSE server on `:8000`; tools in `friday/tools/` (web, system, utils), prompts in `friday/prompts/`, resources `friday://info`.
- `agent_friday.py` → `friday_voice`: LiveKit Agents `AgentSession` with silero VAD, turn detection + endpointing delay; MCP server attached as a tool source (`MCPServerHTTP` SSE).
Small and clear 19-file repo.

**Voice/STT/TTS.** LiveKit voice pipeline, per-user configurable provider constants at the top of `agent_friday.py`:
- STT: **Sarvam Saaras v3** (default, Indian-English optimized) or OpenAI Whisper (`STT_PROVIDER`).
- LLM: **Gemini 2.5 Flash** (default) or GPT-4o (`LLM_PROVIDER`).
- TTS: **OpenAI tts-1 / nova voice** (default) or Sarvam Bulbul v3 (`TTS_PROVIDER`).
- VAD: silero; endpointing tuned per STT (0.07 s sarvam / 0.3 s whisper).
- Runbook: requires LiveKit Cloud project; runtime in a LiveKit room (dev mode via LiveKit Agents Playground).

**Agent architecture.** LiveKit `Agent` subclass `FridayAgent` with a large `SYSTEM_PROMPT` engineering the persona (call tools silently, 2–4 sentence spoken replies, in-character triggers, no markdown). Greeting varies by time of day in `on_enter`. No memory, no multi-step planning.

**Tools/MCP.** MCP server exposing: `get_world_news`, `get_world_finance_news`, `search_web` (stub), `fetch_url`, `open_world_monitor` (launches browser URL), `open_finance_world_monitor`, `get_current_time`, `get_system_info`, `format_json`, `word_count`. Registration pattern: each tool file exports `register(mcp)`, wired in `friday/tools/__init__.py`; new tools auto-picked-up.

**Memory.** None.

**Desktop control.** `open_world_monitor*` only — opens a web dashboard in the system browser via `webbrowser`.

**UI.** LiveKit Playground browser room (voice chat); the repo has no own UI.

**Model providers.** Cloud-only: Sarvam, OpenAI, Google Gemini (STT/LLM/TTS providers pluggable). No local models.

**Security/permissions.** Env-driven keys (`.env.example`; `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `LIVEKIT_*`, `SARVAM_API_KEY`, optional GROQ/DEEPGRAM/SUPABASE). No sandboxing (MCP tools are trusted). MCP server binds localhost by default.

**Dependencies.** `fastmcp`, `httpx`, `livekit-agents[deepgram,groq,openai,sarvam,silero]>=1.5.1`, `livekit-plugins-google>=1.5.1`, `python-dotenv`.

**Strongest components for YORU.** The **MCP-server + realtime-voice-agent wiring pattern** (LiveKit `AgentSession` + `mcp_servers` as tool source); clean two-process split (brain-backend vs voice agent); provider-swap constants; FastMCP tool registration convention.

**Weaknesses.** Demo-grade: news RSS reader + stub search; no memory/state; cloud-everything (no local inference); depends on LiveKit Cloud rooms (network round-trip); **missing LICENSE file** in repo (README merely claims MIT); WSL-oriented (MCP URL auto-resolution from WSL → Windows host).

**License restrictions.** ⚠️ **User-reported direct permission (recorded separately from public licensing):** the user states Sagar Tamang personally gave them permission to use his FRIDAY system. This is a **direct grant from the rights holder for this project**, recorded here as a user-reported fact. It does **not** change the public licensing of the repository itself: no LICENSE file exists at the inspected commit (`4d85750`), so **do not claim the repository or its code is MIT**. The existing prototype already codified this split in `integrations/friday/upstream/PROVENANCE.json` ("User reports direct permission from Sagar Tamang to use his system. No LICENSE file present at inspected commit. No broader redistribution grant inferred.").

**Can actual source be incorporated?** **Yes — limited to this project's scope.** Use and modify Sagar Tamang's system per the owner's direct grant. Scope of the grant is the user's report; no broader redistribution license is established by the repository, and any public distribution of a derivative should be verified with the owner before release. Added value to the YORU donor map: utility modules (`system.py`, `utils.py`) and the MCP-tool/file-registration convention — re-derived, not wholesale ported.

---

### 3.6 jdrurka/jarvis-demo — `D:\YORU\upstream\jarvis-demo`

**Purpose.** "Build a JARVIS": hold a key → speak → your words go to **Claude Code running headless** on your machine → reply streams back in a cloned voice while a full-screen particle figure ("Sentinel") reacts. Ask it to *build* and it spawns a second Claude Code session with file tools, does the work, and tells you when it's done. Runs on your Claude subscription — **no Anthropic API key**.

**Architecture.** Small Node/TypeScript monorepo-in-one:
- `server.js` — static files + WebSocket (loopback `127.0.0.1:3210` only), `/stt` endpoint, streaming turn protocol (binary frames: `pcm_meta / state / stats / sentence / pcm`), one-build-at-a-time guard.
- `lib/brain.js` / `lib/brain-stream.mjs` — "the seam": spawn `claude -p`, tools off for chat, stream-json for streaming replies, sentence splitting for live TTS.
- `lib/builder.js` — spawns Claude with `Write/Edit/Read` in a fresh `builds/<timestamp>/`, enforces timeout, denies escaping tools + writes to protected paths.
- `primitives/*.mjs` — declarative "kinds of build" → `id, triggers, questions, systemPrompt, allowedTools, mcp, outputContract, doneLine, timeoutMs`; registry auto-loads; persona auto-generated from registry.
- `client/` — Vite/TS browser app: Sentinel figure (three.js), frame decoder + streamed PCM player, push-to-talk.

**Voice/STT/TTS.**
- STT: browser MediaRecorder → POST `/stt` → **OpenAI Whisper** (`lib/stt.mjs`; content-type→extension mapping since Whisper keys off filename).
- LLM: headless `claude -p` (pinned `claude-haiku-4-5-20251001`, `--allowedTools ""` for chat; `--permission-mode acceptEdits` + per-build deny `settings.json` for builds).
- TTS: **Fish Audio S2.1** (`lib/fish-live.mjs` streaming WebSocket — sentence in, raw PCM out; `lib/tts.js` buffered fallback); config at `~/.config/fish-audio/speak.json`.

**Agent architecture.** Two Claude sessions: fast chat (tools off) and autonomous build (file tools on). Machine-tag dispatch: chat model appends `[ACTION:BUILD primitive=<id> key=value ...]`, server parses/strips before anything is spoken, one question at a time, then `builder.run()` returns a structured `{ok, artifact, result, log, timedOut}` outcome.

**Tools/MCP.** Claude Code tool surface: chat = none; build = `Write, Edit, Read` (+ optional `mcp__<server>` slots granted only if configured on-machine). Hard deny floor in `lib/builder.js`: `Bash, BashOutput, KillShell, Task, WebFetch, WebSearch` removed unless explicitly granted.

**Memory.** Ephemeral: per-tab Claude session (`sessionId` threaded through `ask(text, sessionId)`); refresh = fresh mind. README explicitly points at the memory seam as the intended growth point (persist sessionId + summary per project, e.g. JSON/SQLite keyed by working directory).

**Desktop control.** Only opening the finished artifact in the browser. Builds run in a fresh subfolder; **permission scoping not a sandbox** (deny-list of `~/.claude/**`, `.ssh`, `.gnupg`, `.aws`, `.config`, PATH dirs, launch agents, `/etc`, `**/.git/hooks/**`, repo source).

**UI.** Browser client: "Sentinel" three.js particle orb reacting to speech state, build HUD, captions, progress list, push-to-talk (hold Space), diagnostics panel (key `d`), hotkey toggles. Streamed PCM playback.

**Model providers.** Claude (subscription) via CLI; OpenAI Whisper; Fish Audio. No local models, no API-key LLM.

**Security/permissions.** Excellent for a small demo: loopback-only server, Host/Origin checks, path-traversal guard, per-build deny-list settings file, process-group SIGTERM/SIGKILL, `MAX_BUILDS=1` global slot, warns plainly it is scoping-not-sandbox (recommends VM/container for real isolation).

**Dependencies.** `@msgpack/msgpack`, `three`, `ws` (runtime); Vite/Vitest/TS (dev). Node ≥20.

**Strongest components for YORU.** The **build-primitive pattern** (declarative one-file capability definitions with questions/tools/output-contract/timeout) maps well onto YORU skills; the **stream-while-you-synthesize** turn protocol (sentence-split → live TTS → PCM frames, cancel path); Claude-Code-as-agent-execution-backend with per-build deny-lists; structured outcome contract for build orchestration.

**Weaknesses.** Claude-subscription-dependent (not provider-neutral); browser-mic-dependent (no native audio); no memory; demo iteration cap (single build slot); macOS/Linux-first (`lib/builder.js` notes Windows lacks process groups); Fish Audio account required.

**License restrictions.** MIT (`LICENSE` present, 1,089 bytes).

**Can actual source be incorporated?** **Yes** (MIT), primarily as reference for the primitive/skill schema, turn streaming protocol, and Claude-code execution sandboxing heuristics — likely re-implemented, not copied wholesale.

---

### 3.7 SAGAR-TAMANG/ultron-by-sagar-builds — `D:\YORU\upstream\ultron-by-sagar-builds`

**Purpose.** "ULTRON Orb UI": an Iron Man–inspired holographic 3D orb controlled with **bare hands through the webcam** (MediaPipe hand tracking). The open-source *interface* of the author's ULTRON AI (a real-time-talking agent that controls Android devices).

**Architecture.** Next.js 16 + React 19 + Three.js. Small:
- `lib/orbScene.ts` — Three.js scene: layered wireframe shells, spiral inner core, floating code-text sprites, orbiting debris, dust particles, scan rings, bloom + chromatic-aberration post-processing.
- `lib/handTracker.ts` — MediaPipe `HandLandmarker` on webcam feed; pinch detection with hysteresis (0.32 on / 0.45 off), one pinched hand spins, two pinch-zoom by spreading; smoothing 0.4; GPU delegate with CPU fallback.
- `components/JarvisOrb.tsx` — HUD + glue (scene, tracker, inputs).
- `app/page.tsx` renders the orb. ~14 files total.

**Voice/STT/TTS.** None.

**Agent architecture.** None (pure frontend visualization). No backend.

**Tools/MCP.** None.

**Memory.** None.

**Desktop control.** None (browser webcam only).

**UI.** The three.js orb is the deliverable — holoscreen aesthetic (wireframe shells, glow, particle dust, scan rings) with controls: mouse drag/scroll, touch, gestures (G to toggle), keyboard (R reset, +/− zoom).

**Model providers.** None (MediaPipe hand-landmark model from Google CDN; one-time load of `hand_landmarker.task` float16).

**Security/permissions.** Webcam permission only (frontend). No server.

**Dependencies.** `@mediapipe/tasks-vision`, `next`, `react`, `react-dom`, `three`; dev TS/types.

**Strongest components for YORU.** The **orb scene** — a polished `three.js` "presence/HUD" visualization for a voice assistant (reacts to state: thinking/speaking/working; the jarvis-demo Sentinel figure shows the same idea at higher polish). Gesture control is a novelty, not core.

**Weaknesses.** Decorative only; no logic, no state machine integration with an agent; no accessibility story; vision model fetched from CDN at runtime.

**License restrictions.** MIT (`LICENSE` present).

**Can actual source be incorporated?** **Yes** (MIT), as a starting point for a YORU "presence" visualization / voice-assistant orb in the desktop UI. Not architecturally meaningful beyond that.

---

### 3.8 msitarzewski/agency-agents — `D:\YORU\upstream\agency-agents`

**Purpose.** "The Agency": a large catalog of **~264 specialized AI agent personalities** (markdown files with YAML frontmatter) plus scripts (and an external app) to convert & install them into many agentic tools: Claude Code, Cursor, Codex, Gemini CLI, Copilot, Qwen Code, OpenCode, Osaurus, Aider, Antigravity, Kimi, OpenClaw, Windsurf, Hermes, Mistral Vibe, ZCode.

**Architecture.** Content + tooling:
- `engineering/ … /specialized/, academic, design, finance, game-development, gis, healthcare, marketing, paid-media, product, project-management, research, sales, security, spatial-computing, support, testing` — markdown personality files, each with frontmatter (`name, description, color, emoji, vibe`) + identity/memory/roles/mission/critical rules/communication style/deliverables.
- `divisions.json` — division ↔ label/icon/color (source of truth, CI-checked vs disk).
- `tools.json` — installer contract per tool (`format`, `installKind` per-agent/roster/plugin, scope user/project, detect dirs, dest templates, slug rules, version cmd).
- `scripts/convert.sh`, `scripts/install.sh`, `scripts/lint-agents.sh` (+ `integrations/` = per-tool converted outputs).
- Companion app `agency-agents-app` (electron/tauri?) is external — installs agents into the listed tools and auto-updates.

**Voice/STT/TTS.** None. One agent personality ("Voice AI Integration Engineer") is a transcription-pipeline domain persona, not a runtime.

**Agent architecture.** None at runtime — a **prompt/roster library**. The "personalities" are written to be compliant with each host tool's agent format (frontmatter identity, sub-agent semantics), including OpenCode's agent-format (note: OpenCode runtime registers ~119 agents max — upstream bug — so the installer warns on over-selection).

**Tools/MCP.** None itself; it *installs* prompt-specs for tools that expose agent/skill/MCP-style abstractions.

**Memory.** None (persona files describe in-character "memory" as role knowledge; no persistent store).

**Desktop control.** None.

**UI.** None in-repo (the app provides browsing/install UI).

**Model providers.** Tool-agnostic (formats target Claude Code, Gemini, Codex, Copilot, Qwen, OpenCode, etc.).

**Security/permissions.** Dependency-free install scripts; `SECURITY.md` present; personality files are inert markdown (no code execution); the app handles install paths.

**Dependencies.** Bash scripts only (no package manifest). Agent content depends on the host tool's agent format.

**Strongest components for YORU.** The **persona-authoring conventions** and the **multi-tool agent-format conversion layer** (`convert.sh`/`install.sh`, per-format renderers producing byte-identical outputs per tools.json `format`) — valuable if YORU exposes sub-agent roles/skills in a standard format. Treasure-trove of well-structured, field-tested "specialist agent" system prompts (frontend dev, appsec, RAG, voice-ai, etc.) usable as YORU role/skill seeds under MIT.

**Weaknesses.** No runtime, no integration with a daemon; personalities are personality-only (no tool code); markdown-only (no executable abstraction); OpenCode agent-count ceiling in the ecosystem.

**License restrictions.** MIT (`LICENSE` present).

**Can actual source be incorporated?** **Yes** (MIT), especially the agent-personality corpus and the conversion/installer scripts. Useful for seeding YORU's own role/skill library (personality + process text) rather than runtime code.

---

### 3.9 Existing YORU prototype (previous build) — REFERENCE-ONLY

> **Status:** This is the user's **own earlier prototype** that the new YORU project replaces. Per the Architecture Rule at the top of this document, it is **donor/reference material only** — it must **not** become the foundation, fork base, or resemble the new build. It is audited here to capture proven solutions, failures, and reusable ideas.

**Location (inspected, NOT modified):** `C:\Users\Admin\Documents\Codex\2026-09-18\referenced-chatgpt-conversation-this-is-an-2\outputs\YORU` (also `outputs\verification\*` evidence next to it).
**Provenance inside the tree:** `docs/source-manifest.json` traces 41 files by SHA-256 to the prior LUNARIS build of 2026-09-17 — the prototype is a direct descendant of the user's earlier LUNARIS lineage (see also `docs/inventory.json` cataloging LUNARIS V21→V25, rebuilt JARVIS, AuroraDayForever/AuroraUE5, etc.).
**Scale:** ~70 source files ≈ 220 KB of authored code (excluding `node_modules` / `dist`). npm deps: `electron ^44`, `electron-builder ^26` (portable win target), `react ^19`, `vite ^7`, `@modelcontextprotocol/sdk ^1.30`.

**Purpose.** "YORU voice island and scoped production agent" (v0.2.0) — a Windows Electron desktop companion: a tiny always-on voice **island** (transparent, frameless, always-on-top) + React settings/management window; local memory, reminders, imported documents, no-key web search and weather; provider-switchable reasoning (cloud-compatible or local Ollama); strict content-scoped **project automation** (AURORA / Unreal source-check harness); external tools via **allowlisted + approval-gated MCP**, and a Windows-native SAPI voice loop (dictation + optional "hey jarvis" wake word).

**Architecture.** Single Electron process; the main process owns every security-sensitive capability; the renderer is sandboxed with a frozen preload API.
- `electron/main.cjs` (135 lines) — Store, Registry, Agent, Provider router, ProjectHarness, MCPBridge, the approval gate, island window manager (morphs), Tray + global hotkey, PowerShell voice children, all `ipcMain.handle` handlers, single-instance lock, telemetry.
- Core (CommonJS): `store.cjs` (state.json, atomic tmp+rename, mode 0600, messages never persisted), `registry.cjs` (tool manifests + arg validation + approval + audit), `orchestrator.cjs` (= `agent.cjs`, bounded ReAct loop, per-turn denied-set), `context.cjs` (system persona + project-work rules + memory/doc passages + timestamp), `cloud.cjs` (= `provider.cjs`, streaming-off OpenAI-compatible router, cloud vs local), `calculator.cjs` (bounded recursive-descent arithmetic), `search.cjs` (DuckDuckGo public HTML, challenge rejection), `dashboard.cjs` (CPU/RAM/disk telemetry + Open-Meteo weather, no API key), `companion.cjs` (state machine), `project.cjs` (scoped project harness), `mcp.cjs` (sdk bridge).
- Plugins: `builtin.cjs` (7 tools), `companion.cjs` (3 tools), `example.cjs` (`word_count`, opt-in by editing main.cjs — disabled by default).
- Renderer: `src/main.jsx` (+ `island.css`) = the current island UI; `src/dashboard.jsx`/`src/companion.jsx` + their css = **two older UI generations that reference a `window.jarvis` preload API that no longer exists** (preload now only exposes `window.yoru`). They are non-functional remnants; only `main.jsx` runs.
- IPC hardening: every `handle()` validates `event.sender` (webContents identity + `mainFrame` + exact `file://` entry URL), else throws "Untrusted sender". Renderer has `sandbox:true`, `contextIsolation:true`, `nodeIntegration:false`, CSP `default-src 'self'`, global permission handlers return `false`, `setWindowOpenHandler` deny, `will-navigate` prevented.

**Voice implementation.**
- `electron/speech.ps1` — SAPI: `-Mode speak` (SpeechSynthesizer, installed voice), `-Mode listen` (SpeechRecognitionEngine dictation: `YORU_SPEECH_LANGUAGE` → CurrentUICulture → en-US → first installed; 8 s initial silence / 700 ms end silence; streams `LEVEL:<0-100>` every ~60 ms to drive the island's energy equalizer; stdin `STOP\n` cancels; 15 s deadline; UTF-8 console I/O).
- `electron/wake.ps1` — dual SAPI recognizers: a "hey jarvis" Choices grammar loop (30 s window) that prints `WAKE`, opens a 10-minute dictation window printing `COMMAND:<text>` per utterance, then `SLEEP`; killed via `wakeChild.kill()` on toggle/quit.
- Flow (`voiceTurn()`): `island('listening')` → listen → empty? → `error` → `island('thinking')` → `agent.chat` → `island('responding')` → `speak(answer.slice(0,4000))` → `island('complete')`.
- Cancellation: `voiceEpoch` counter makes stale turns self-abort; Ctrl+Alt+Space toggles talk/cancel; double-click island cancels; `cancel` IPC kills speech child and clears any pending permission.
- ⚠️ **Wake word is disabled in this release**: `handle('wake-toggle')` throws "Wake-word support is not enabled in this release. Activate the island to talk." for enable=true — yet the older dashboard generation still advertises the toggle (a dead-UI pairing).
- `scripts/speech-diagnostic.ps1` — no-microphone end-to-end proof: synthesize "What time is it?" (Microsoft Zira Desktop) to a WAV, then dictate the WAV and print transcript + confidence.
- `scripts/doctor.cjs` — health report: node/platform, cloud-config presence, AURORA existence, installed SAPI recognizers + voices, local Ollama model list.
- Weaknesses: SAPI-only quality/language availability varies by installed speech pack; PowerShell child per voice action; timeouts (listen 20 s / speak 60 s) and any stderr → hard fail.

**Island states.** Two overlapping vocabularies exist:
- `core/companion.cjs` `Companion.STATES`: `idle, listening, thinking, working, permission-needed, finished, error, sleeping, automation-triggered` (EventEmitter, used for the "sleep" flow + reminders).
- Renderer island states (`island()` in main.cjs) with per-state window sizes: `idle [116,48], listening [240,52], thinking [136,48], acting [280,52], permission [360,100], responding [190,52], complete [146,48], error [310,64]`; 210 ms cubic-ease morph (`morphTimer`, 16 ms interval), centered-top of the current display, transparent rounded shell (`setShape` on Windows), `permission` is the only focusable state; `complete`→idle after 1.5 s, `error`→idle after 6 s.
- The state-name drift (`working` vs `acting`, `permission-needed` vs `permission`, `finished` vs `complete`) is a double-bookkeeping smell worth avoiding in the fresh build.
- `outputs/verification/*` prove the island harness ran: PNG per state + `report.json` asserting bounds/focusability/transparency/text for all 8 states (e.g. `permission` 360×100 focusable:true; others focusable:false).

**Provider switching.** `core/cloud.cjs`: `settings.provider ∈ {cloud, local}`.
- cloud → `YORU_API_URL`/`YORU_API_KEY` env; requires **HTTPS**, no embedded credentials; model from `YORU_MODEL` or `settings.model`; request `{model, messages, tools, stream:false}` with Bearer auth; ≤3 attempts with exponential backoff on 429/502/503/504; 90 s AbortSignal timeout.
- local → `YORU_LOCAL_URL` default `http://127.0.0.1:11434/v1/chat/completions`, loopback-only (127.0.0.1/::1, http/https).
- Switching via Settings IPC validates shape, and switching **to cloud requires an explicit approval** (`cloud_context_sharing`) because saved memories + document passages will be sent out.
- Legacy generations had a third `ollama` label; current UI reduced to cloud/local. `provider.test.cjs` pins the contract (request shape, secret hygiene on errors, HTTPS enforcement).

**Permissions.**
- `Registry.execute()` order: tool-exists → args object → property allowlist → required args → type/length/enum/number bounds (string maxLength default 10 000; number 0..1e9) → abort check → optional `prepare()` review → **approval gate** → `run()` → abort check → `audit()`. Approval surfaces as the island `permission` state with Deny/Allow-once (and `Review edit` → full before/after diff in Settings for `project_edit`).
- Denied actions are **sticky for the turn**: the orchestrator keeps a `denied` Set and replies "User denied this tool for this turn. Do not retry."
- Approved-by-default (metadata): clock, calculator, notes_list, document_search, project_list/inspect/read/commands/evidence. Approval-required: memory_save, file_write, app_launch, web_search, reminder_create, document_read, project_edit, project_run, weather_lookup, open_website, browser_search, connect_mcp, open_output_folder, cloud_context_sharing.
- MCP: loopback-only URL, tool-name **allowlist**, shallow property validator, names prefixed `mcp_` (≤41 chars), **every call approval:true**, 30 s call timeout, connect/list timeout 10 s.
- Store privacy: `state.json` persists memories/documents/settings/logs but **never messages** (exported via dialog when the user asks); file mode 0600; corrupt state fails startup explicitly instead of silent reset.

**AURORA harness.**
- `config/projects.json` — only approved projects; AURORA = root `D:/AURORA/AuroraUE5` + allowlisted `source_check` command → `node scripts/aurora-check.cjs <root>`.
- `core/project.cjs` `ProjectHarness`: scoped path entry (rejects absolute/`..`/`:`/ADS `foo.txt:secret`, `.env*`, credentials/secrets/api-key naming, trailing-dot names, null byte), blocks `.git .env .ssh .aws .azure .codex .agents node_modules .venv venv AppData`, TEXT extension allowlist, symlink/junction rejection, 128 KB read cap.
- Tools: `project_list`, `project_inspect`, `project_read` (returns sha256), `project_edit` (**expected_sha256** optimistic concurrency; `NEW` hash = create; rejects hardlinks; writes checkpoint JSON to `userData/checkpoints` before an atomic temp+rename; verifies sha256 after), `project_commands` (owner-allowlisted: absolute executable + explicit string-array args, **no** `.cmd/.bat/.ps1`), `project_run` (approval; env scrubbed to 5 vars; 120 s timeout; `taskkill /PID /T /F` on cancel; 24 KB output cap; `verified = exit 0 && !cancelled && !timedOut`; run record to `userData/runs`), `project_evidence` (last 20 records).
- `scripts/aurora-check.cjs` — **read-only** source check: `.uproject` + README + 3 AURORA bibles presence, `.uproject` JSON parse, walks `SourceArt/` and validates every `.gltf`'s buffer/image URIs resolve inside the project (value `data:` excluded); never starts the engine; exit code 1 on any error.
- `scripts/check-friday.cjs` — connects the real `MCPBridge` to a running localhost MCP server (approve→true) and executes live tools.

**Tests.** `npm test` = `node --test tests/*.test.cjs`.
- Unit suites: `core.test.cjs` (13 cases — denied actions never mutate; tool-boundary rejections incl. unknown/extra-arg/type/number; file_write create/traversal/CON-name/overwrite; persistence + deletion; retrieval ranking + source; reminder catch-up; agent tool-loop feeding; provider failure explicit; **loop bounded to 16**; concurrent chat rejected; cancel-during-approval prevents mutation), `project.test.cjs` (boundary incl. ADS; denied edit leaves no checkpoint; stale expected-hash rejected; checkpoint recovery; **agent repairs a real failing process, re-runs it, observes pass, reports evidence**; cancel kills process and never verifies; model cannot mark an untested edit verified), `conversation.test.cjs`, `mcp.test.cjs` (real in-process streamable-HTTP MCP server fixture; allowlist + denial + approval-then-call), `provider.test.cjs`, `search.test.cjs` (+ weather + telemetry), `companion.test.cjs` (calculator, state machine, notes/documents approval + restart privacy).
- Electron smoke (manual): `desktop-smoke.cjs` and `lunaris-smoke.cjs` target the **old** `window.jarvis` generations (dashboard `.settings-trigger`, companion 180→560 px panel) and are **stale** vs the current `window.yoru` island UI. `island-desktop.cjs` targets the current island (iterates all 8 states via `window.yoru.demo()`, dumps PNGs + report.json to `verification/`).
- Lesson for the new YORU: the prototype shipped **two stale desktop harnesses and one current one** — UI/tests drifted. The fresh build must keep exactly one harness per surface, updated with every UI change.

**Successes (proven ideas worth re-deriving).** Bounded ReAct loop (16 steps) with per-turn sticky denial; argument-manifest validation at the tool boundary; approval+audit as a hard gate before any mutation; checkpointed exact-content writes with SHA-256 optimistic concurrency and the hard rule that "an edit is not a verified build"; explicit build-verification language in the agent's answer; provider contract with **secret hygiene on errors**; single-instance lock; sender-validated IPC; sandboxed, CSP-locked renderer; loopback-only, allowlisted, per-call-approved MCP; no-key search (DuckDuckGo HTML with challenge rejection) and no-key weather (Open-Meteo, main-process fetch); sticky JSON store with atomic tmp+rename + 0600; reminders with single-fire + repeat catch-up on reopen; read-only AURORA harness that never mutates the project; the "preview before write" edit UX; privacy-by-persistence (messages never written to disk).

**Failures / lessons.** Stale desktop tests vs current UI (dead `window.jarvis` API references); wake word advertised in an old UI but disabled in code; `package.json`'s `build.files` references `docs/ATTRIBUTION.md` which is **missing from the tree** (portable build would ship without its attribution); two state vocabularies (`Companion.STATES` vs island states); env-only configuration (`.env.example` is documentation, not auto-loaded — no dotenv); SAPI-only voice (language-pack dependence, moderate dictation quality); full-JSON synchronous rewrite of `state.json` on every message; junk dirs in the prototype root (`�` empty dir and `???\default.dic`, likely zip-extraction artifacts).

**Reusable code (donor inventory for the fresh YORU).** The ideas and modules above are candidates to re-derive (origin: user's own previous work — see `docs/source-manifest.json`). Specifically: `registry.cjs`, `orchestrator.cjs`, `cloud.cjs` adapter/router, `store.cjs`+`retrieve()`, `calculator.cjs`, `search.cjs`, `dashboard.cjs` telemetry/weather, `mcp.cjs`, `project.cjs` harness, `aurora-check.cjs`, `doctor.cjs`, the `Companion` state machine, the island morph + inline-permission UI concept, `speech.ps1`/`wake.ps1`/`speech-diagnostic.ps1` patterns, the skills/*.md pattern, and the `island-desktop.cjs` screenshot harness.

**License.** The prototype carries **no LICENSE file** of its own (author "JARVIS contributors"; it is the user's previous build, treated as user-owned reference material). `docs/Mark-LIV-LICENSE.txt` = **Mark LIV — JARVIS © 2026 FatihMakes, CC BY-NC 4.0** (non-commercial license governing the separately-delivered Mark-LIV asset). `integrations/friday/upstream/PROVENANCE.json` = Sagar Tamang direct-use permission record (see §3.5). **Not modifiable from the new build's perspective** — any reuse must respect those rights and the Architecture Rule.

---

### 3.10 Mark-LIV — `D:\Downloads\Mark-LIV-main.zip` — REFERENCE-ONLY (CC BY-NC 4.0)

> **Status:** Audited from the user-provided archive (430.1 KB, modified 09/17/2026), extracted read-only to `C:\Users\Admin\AppData\Local\Temp\opencode\mark-liv\Mark-LIV-main`. **Original zip NOT modified.** Per the Architecture Rule this is donor/reference material only; additionally its **non-commercial license forbids vendoring code into any commercial YORU build.**

**Provenance.** Repository `FatihMakes/MARK-LIV`, author name "Mark LIV" / README title **"MARK LIV (54)"** by FatihMakes — "The Ultimate Cross-Platform Personal AI Assistant". In-repo `LICENSE` = **MARK LIV — JARVIS, Copyright (c) 2026 FatihMakes, CC BY-NC 4.0 (commercial use not permitted)**. Same 19,682-byte text already recorded in the prototype's `docs/Mark-LIV-LICENSE.txt` (confirmed byte-size match) — Mark-LIV is the separately-delivered asset the earlier YORU prototype referenced.

**Scale.** Python 3.11–3.13, PyQt6. Two monoliths dominate: `main.py` 113,625 B (2,284 lines) and `ui.py` 233,099 B (5,438 lines). Also `setup.py`, `requirements.txt`, `readme.md` (36,840 B), `config/` (`__init__.py`, `jarvis.ico`), `memory/` (memory_manager.py 18 KB, config_manager.py 14 KB), `dashboard/` (server.py 38 KB, static/login.html + app.html + crypto-js.min.js), 22 auto-discovered `actions/*.py` (incl. browser_control 44 KB, computer_settings 39 KB, file_processor 39 KB, game_updater 43 KB, file_controller 28 KB, dev_agent 21 KB, computer_control ~19 KB, web_search 15 KB), `core/` (avatar.py 36 KB + avatar_mesh.py + face_model.obj 25 KB, action_loader.py, plugin_loader.py, prompt.txt 9.5 KB, echo.py, hotkey.py, wake_word.py, undo.py, confirm.py, viseme.py, audio_devices.py, gemini.py, installer.py, stt.py, tts.py, llm_client.py), `plugins/_template.py`.

**Architecture.** Single-process asyncio + Qt desktop app. `main.py::JarvisLive` owns a reconnect-forever `run()` loop: builds a `LiveConnectConfig` from live registries + config + memory, connects to Google **Gemini Live API** (`models/gemini-3.1-flash-live-preview`, 16 kHz mic / 24 kHz out), runs a `TaskGroup` of coroutines (`_send_realtime`, `_listen_audio`, `_receive_audio`, `_play_audio`, reconnector watch, system monitor, background monitor, proactive engine, sleep watch, phone-audio relay), and rebuilds the session on demand. Key architectural decisions:
- **Session resumption:** server-issued resumption handles kept **in RAM only** (never persisted — persisting would break the session-summary/morning-briefing flow); `resumable` flag gates capture; handles are replayed across reconnects so a voice or audio-device change keeps the conversation. Voluntary reconnect signal (`_ReconnectSignal`) unwinds the TaskGroup cleanly; a fresh client is built per reconnect; context-window sliding-window compression keeps one session alive for hours.
- **Tool discovery:** inline tools live in `main.py` when woven into session state (system_status, screen_process, close_camera, manage_monitor, shutdown_jarvis, save_memory, recall_memory, undo). Everything else is **auto-discovered**: `core/action_loader.py` scans `actions/*.py` for a module-level `TOOL` dict (name/description/parameters/handler + optional `behavior` BLOCKING|NON_BLOCKING and `scheduling` WHEN_IDLE|SILENT|INTERRUPT); `core/plugin_loader.py` does the same for `plugins/` with an extra `PLUGIN_SETTINGS` schema (namespaced config forms rendered by the UI, no core edit needed). Name collisions with inline tools are rejected; import/validation errors are logged and skipped — **never raises out of discovery**. Handlers are invoked by signature introspection (only receive the `player`/`speak`/`response`/`session_memory` kwargs they declare).
- **System prompt derived, not hand-written:** `core/prompt.txt` (9.5 KB) holds `{assistant_name}`, `{platform}`, `{capabilities}`, `{limits}` tokens filled at connect time from the live action/plugin registries and host; IDENTITY/ADDRESS block injected (name + respectful-address rule per language); memory block + timestamp prepended. Limits are stated as architecture ("anything not listed is out of reach"), not as a refusal list.
- **UI:** `ui.py::JarvisUI` → `MainWindow` with a `HudCanvas` (state machine INITIALISING/LISTENING/THINKING/PROCESSING/SPEAKING/SLEEPING + waveform + face/core HUD styles), `HoloAvatar` (software-rendered via QPainter + numpy, no GPU), `_SysMetrics` (CPU/RAM/GPU/temp loop), `LogWidget`, `FileDropZone`, `MetricBar`, and a thread-safe signal-based surface for actions (set_state, write_log, show_content, push_visemes, camera stream, quiz/review overlays, confirm banner). `main()` also patches `subprocess.Popen` on Windows with `CREATE_NO_WINDOW` and reconfigures stdout/stderr to UTF-8+replace so emoji status lines survive any code page.

**Voice pipeline (the standout).**
- `_listen_audio` gates the mic: wake-word asleep → frames go to the local detector only, **nothing streamed to Gemini**; while speaking → mic not streamed (voice barge-in implemented in `core/echo.py` but **disabled pending hardware testing**); echo tail → `EchoGuard` classifies blocks by subtracting the echoed band energies of what we just played, dropping only our own voice while still letting a real reply through; push-to-talk closes the mic unless the chord is held. Echo tail is sized from the **measured** output latency (`stream.latency`), not a guess.
- `_play_audio` batches queued 24 kHz chunks (~200 ms), computes a **viseme schedule** per 20 ms (`_pcm_visemes`: F1→openness, F2→width bands, fricative hiss gate, hanning window) and drives the avatar's mouth against a **play-cursor timeline** that starts from `now + one callback period` (`_FIRST_SOUND`), re-anchored only when it drifts out of the physically possible window. `core/viseme.py` fuses transcript shapes onto that timing: text supplies *which* shape (Unicode-decomposed + Cyrillic/Greek transliteration → 26 letters → 13 visemes; CJK/Arabic fall back to audio-only), audio supplies *when/how strongly*. Language-independent by construction.
- `core/audio_devices.py` picks devices by **name, not index** (indices shift on plug/unplug), by *measuring* reality instead of reasoning: it opens a real stream per host API (`_usable`) and **probes whether the transport actually moves audio** (`_transport_works` — DirectSound output is a silent sink, MME truncates names to 31 chars; so per-direction API selection e.g. DirectSound input + MME output on Windows). Cached on a background thread; a saved-but-gone device degrades to the OS default instead of crashing.
- Wake word: `core/wake_word.py` uses openwakeword "hey_jarvis", **lazy import** (zero cost when off), detector in its own thread fed nonblocking from the mic callback, 16 kHz int16, threshold 0.5, fully local after a one-time model download; auto-sleeps after 120 s of silence; UI toggles report need_download/enabled/disabled.
- Prebuilt Live voices (Charon/Puck/Kore/Fenrir/Aoede) via `speech_config`; turn-tuning (`automatic_activity_detection` silence/prefix/sensitivity knobs) and media resolution + thinking config are optional preview-API fields that **self-disable** (`_tuned_live`/`_enhanced_live`) on server rejection rather than block startup.

**Legacy/unused paths.** `core/stt.py` (faster-whisper/Vosk), `core/tts.py` (EdgeTTS/Kokoro/ElevenLabs), `core/llm_client.py` (ollama/openai-compat), `core/installer.py`, and `setup.py` (an auto-installer) all carry "MARK XL" docstrings and are **not imported by `main.py`** — the Live API handles STT+TTS+TTS-model and the local-LLM path is dead code. Only `core/gemini.py` (one-shot calls, fallback ladder, throwaway session) is actually used (session summaries, web_search grounding, code tools).

**Actions (tools).** Notable implementations: `computer_settings.py` (pyautogui/pycaw/WMI volume, brightness, dark mode, wifi, restart/shutdown; **captures "before" values to register every volume/brightness/dark-mode change with `core.undo.push_undo`**; full action vocabulary spelled out in the TOOL schema so no second Gemini call is needed; restart/shutdown/toggle_wifi sit behind `_IRREVERSIBLE` → `confirm.request`); `file_controller.py` (create/write/delete/move/copy/rename/organize-desktop, each pushing an undo closure; write undo skips binary/locked/oversized); `screen_processor.py` (camera/screen capture with compression + camera-index probing); `web_search.py` (Gemini grounded search with a 429 circuit breaker cooldown → duckduckgo `ddgs` fallback, bounded timeout threads); `computer_control.py` (cursor/click/type/drag/screenshots/media; `_screen_find` looks for UI elements via screenshot+contrast); `browser_control.py` (Playwright: goto/type/click/screenshot/extract); `code_helper.py` (write/fix/run/explain/screen-debug via Gemini); plus open_app (fuzzy per-OS app launch), flight_finder (Google Flights scrape + Gemini parse), youtube_video, game_updater, file_processor (doc/ppt/xlsx), dev_agent, weather_report, reminder, send_message, desktop, system_monitor, background_monitor.

**Memory.** `memory/memory_manager.py`: `long_term.json` (identity/preferences/projects/relationships/wishes/notes + `sessions`). **Two-tier prompt design**: identity always in full; ~900-char recency-ranked core block capped at 6 entries/category; then a `[ALSO REMEMBERED]` **key index** (~420 chars) so the model knows a value exists before calling `recall_memory` — turns recall from a gamble into a lookup. `recall_memory` = cheap lexical scoring (no embeddings). Trims oldest by `updated` with a user-facing notifier ("Memory full — forgot X"); runaway guard at 200 KB. Session summaries (1–2 sentences via `gemini.text` in the user's language) appended, popped once by the next morning briefing.

**Remote dashboard.** `dashboard/server.py`: FastAPI + uvicorn on port 8000 (+8001 HTTPS alias); **self-signed TLS pair generated per install, never shipped**; app-layer **AES-256-CBC** with a key derived from the 6-character one-time pairing key (CryptoJS on the client); Bearer session tokens in sessionStorage; permanent device tokens (revocable); <a download> file sharing with sanitized filenames; phone mic → Gemini Live relay; firewall auto-config via an elevated netsh .bat (UAC). Good security posture for this category (TLS + AES + one-time keys) — still, plain-HTTP fallback exists when `cryptography` is missing.

**Security model.** Two real gates: the **forged-proof confirm gate** (`core/confirm.py` — the UI issues a token the model cannot write; replaces a forgeable `confirmed:yes` param; used only for `_IRREVERSIBLE` actions) and the **wake/PTT mic gates** (nothing leaves the machine while asleep/not-holding). **Not present:** per-tool RBAC/allowlists/audit log, project scoping, sender-validated IPC concept (single process), secret-at-rest encryption (`config/api_keys.json` is plaintext JSON, also used for assistant/user names, voice, all toggles — a config file doubling as a key store). The model can freely drive mouse/keyboard, send messages, install/update software — only irreversible settings require a human button.

**Strengths (proven ideas worth re-deriving).** Echo tail sized from measured output latency + band-energy echo classification; barge-in design that is disabled until hardware-tested rather than shipped broken; transcript+audio fused viseme mouth; frame-rate-independent time-constant animation (`_TAU_*`); play-cursor timeline instead of "now"; device selection by *measuring* transports; session resumption kept RAM-only + `resumable`-flag capture; graceful-degradation everywhere (device fallbacks, API fallback ladders, tuning self-disable, "must never raise" loaders); action/plugin discovery where the model's capability list is derived from what is actually installed; `scheduling` (WHEN_IDLE/SILENT/INTERRUPT) so a NON_BLOCKING tool result doesn't talk over the user; undo closures for settings+files; per-plugin settings-schema forms; two-phase morning briefing (instant greeting, then background-fetched news, no tool round-trip); proactive engine with time-of-day + rotating focus + silence gates; system/background monitors that never interrupt speech; UTF-8 console hardening + CREATE_NO_WINDOW patch.

**Weaknesses / lessons.** CC BY-NC 4.0 blocks commercial code reuse outright; giant monoliths (main.py 2,284 lines, ui.py 5,438 lines) breed drift; shipped-but-unused "MARK XL" STT/TTS/local-LLM/installer code paths are dead weight; hardcoded Live model string + single-provider dependency (Gemini Live — the whole ingest/echo/viseme pipeline is tuned to its 16/24 kHz contract); config file doubles as the key store (plaintext); verbose self-analysis prose in module docstrings (great for onboarding, costly to maintain); no RBAC/audit/allowlists for most tools; barge-in intentionally disabled. **For YORU this is a reference for UX and voice-pipeline ideas to re-implement under our own architecture, not code to copy.**

**Reusable ideas (donor inventory).** Voice gait: measured-latency echo tail, EchoGuard band-energy classification, wake/PTT mic gating, play-cursor mouth timeline, viseme fusion (transcript shapes + audio formants), software-rendered avatar with time-constant smoothing; session resumption (RAM-only) + voluntary-reconnect signal; tool/plugin auto-discovery with per-file isolation and derived capability list; forged-proof confirm gate; undoable settings/files; two-tier memory prompt (core + [ALSO REMEMBERED] index) + lexical recall; scheduling channels for async tool results; two-phase briefing; proactive/background-monitor engines with speech-respect gates; device-by-name + measured-transport probing; self-signed-once dashboard with app-layer AES + one-time pairing keys.

**License.** CC BY-NC 4.0 (© 2026 FatihMakes) — the in-repo `LICENSE` matches the prototype's `docs/Mark-LIV-LICENSE.txt` (19,682 B). **Permitted: non-commercial use, sharing with attribution, adaptation for non-commercial use. Not permitted: commercial use of any shared/adapted material.** No OSI open-source compatibility. Not modifiable from the new build's perspective — see § Architecture Rule and DONOR MATRIX.

---

## 4. Cross-cutting comparison

| Capability | OpenJarvis | vierisid/jarvis | handy | OmniVoice | friday | jarvis-demo | ultron | agency-agents |
|---|---|---|---|---|---|---|---|---|
| License | Apache-2.0 | **RSALv2-based (source-avail.)** | MIT (+branding) | Apache-2.0 | **no LICENSE file** | MIT | MIT | MIT |
| Runtime lang | Python + Rust(PyO3) | Bun/TS + Go | Rust/Tauri | Python/torch | Python | Node | Next/TS | Bash/MD |
| Native Windows | partial (desktop app, no Win32) | sidecar-only (Win32 UIA) | **strong** | CUDA ok | via WSL | WSL | browser | n/a |
| Agent loop | ✅ many | ✅ + sub-agents | ❌ | ❌ | track-level | Claude-Code | ❌ | ❌ |
| Wake word / always-listen | ❌ | ✅ openwakeword | ❌ | ❌ | LiveKit room | push-to-talk | ❌ | ❌ |
| Local STT | ✅ faster-whisper | ❌ (cloud) | ✅✅ Whisper/Parakeet | ASR only | ✅ Sarvam/Whisper | ✅ Whisper(cloud) | ❌ | ❌ |
| TTS | ✅ Kokoro/OpenAI/Cartesia | ✅ Edge/ElevenLabs | ❌ | ✅✅ cloning/design | ✅ OpenAI/Sarvam | ✅ Fish | ❌ | ❌ |
| MCP | ✅✅ client+server | ❌ (internal tools) | ❌ | ❌ | ✅✅ FastMCP+LiveKit | partial (mcp__ slots) | ❌ | ❌ |
| Memory | ✅✅ facts+vectors+persona | ✅✅ KG vault | transcript history | prompts only | ❌ | ephemeral | ❌ | ❌ |
| Desktop control | ❌ | ✅✅ Win32 UIA + OCR + sidecar | ✅ clip/paste/inject | ❌ | browser-open | ❌ | ❌ | ❌ |
| Authority/permissions | ✅✅ RBAC+sandbox | ✅✅ approval+audit | OS perms | usage disclaimer | env keys | deny-lists | webcam | n/a |
| Workflow automation | schedule + skills | ✅✅ 50+ nodes, 656 pieces | ❌ | ❌ | ❌ | primitives | ❌ | ❌ |
| UI | Tauri + web + TUI | React rooms + pebble | Tauri settings | Gradio | LiveKit playground | three.js client | three.js orb | external app |

---

## 5. Recommended YORU donor map (for the later build phase — *not performed now*)

> **Constraint:** All entries below are donors, not foundations. The new YORU is implemented **inside `D:\YORU\app` only**, from its own architecture. Borrowed components must record origin, license, and reason (§ Architecture Rule).

Pragmatic shape for YORU = **one coherent Windows desktop AI agent**:

1. **Agent core / orchestration / memory / security RBAC / MCP client** — study **OpenJarvis** (Apache-2.0): `core/registry`, agent loops, `security/capabilities`, `mcp/`, `memory/`, engine abstractions. This is the backbone *reference*.
2. **Voice input (STT/VAD/audio capture) + text injection (reliable paste/typing)** — from **handy** (MIT). `audio_toolkit/`, `managers/{audio,transcription}`, `clipboard.rs`/Reliable Paste, `handy-keys` hotkeys, `signal_handle` remote control. Rebrand.
3. **Assistant voice (TTS / voice cloning / voice design)** — from **OmniVoice** (Apache-2.0) as an isolated Python sidecar (subprocess), precomputing a `VoiceClonePrompt` for a stable voice; fallback to a lighter local TTS (e.g. Kokoro, as OpenJarvis uses) for low-latency turns.
4. **Desktop control / Win32 automation / continuous screen awareness** — re-implemented from the **vierisid/jarvis sidecar** blueprint (Win32 UIA, screenshots, OCR, awareness pipeline). Reference-only due to license; write fresh Go or Rust.
5. **Skills / build-primitives / persona roster** — adopt jarvis-demo's **primitive schema** + OpenJarvis' **agentskills.io** skills standard; seed role/personality content from **agency-agents** (MIT).
6. **Presence / HUD visualization** — the three.js orb conception from **ultron** (MIT) and the Sentinel figure from **jarvis-demo** (MIT) as UI inspiration for YORU's voice agent surface.
7. **MCP + realtime-voice bridge convention** — from **friday** (patterns/code per the user-reported direct permission; repo license unverified — see §3.5).
8. **Previous YORU prototype (user's own build, §3.9)** — re-derive its proven patterns into fresh modules: bounded ReAct loop with per-turn sticky denial, argument-manifest tool boundary, approval+audit gate, checkpointed exact-content writes w/ SHA-256 concurrency and "an edit is not a verified build", provider contract w/ secret hygiene, sender-validated IPC + sandboxed CSP renderer, loopback+allowlist+per-approval MCP, no-key search/weather, privacy-by-persistence. Do **not** lift the structure wholesale — the new YORU needs its own architecture and module boundaries.

### License decisions summary
| Repo | Incorporate source? | Constraint |
|---|---|---|
| OpenJarvis | ✅ Yes | Apache-2.0 attribution |
| handy | ✅ Yes | MIT + rebrand (no Handy name/logo) |
| OmniVoice | ✅ Yes | Apache-2.0 + cloning-usage consent rules |
| jarvis-demo | ✅ Yes | MIT |
| ultron-by-sagar-builds | ✅ Yes | MIT |
| agency-agents | ✅ Yes | MIT |
| friday-tony-stark-demo | ✅ user-reported direct permission | Owner (Sagar Tamang) granted use directly (recorded separately). Repo itself: **no LICENSE file → do not claim MIT**; verify with owner before any public redistribution |
| vierisid/jarvis | ⛔ No | Source-available (RSALv2-based); patterns only |
| Mark-LIV (§3.10) | ⛔ No | **CC BY-NC 4.0** (© 2026 FatihMakes) — non-commercial only; ideas → re-implement, never vendored |
| Existing YORU prototype (§3.9) | 🔶 Re-derive ideas only | User's own prior build (no LICENSE file); Mark-LIV asset under CC BY-NC 4.0 (© FatihMakes). Fresh YORU must NOT be its base/fork (§ Architecture Rule) |

---

## 6. Notes / caveats

- `friday-tony-stark-demo`: repository has **no LICENSE file** (README alone claims MIT) — **do not claim the repo is MIT**. Usage is per **user-reported direct permission** from Sagar Tamang, recorded separately.
- `handy` README "feature freeze" + brand-not-open-source caveats must be respected in any fork.
- `vierisid/jarvis` README figures are partially inaccurate vs source (tool counts, OCR engine, specialist count); the audit cites **source-verified** numbers.
- Telemetry: `vierisid/jarvis` ships opt-out telemetry; YORU must avoid copying that or implement explicit opt-in.
- OmniVoice `README` disclaimer prohibits unauthorized voice cloning/impersonation — applies to YORU's use of the generated voices.
- Existing YORU prototype (§3.9): carries stale desktop tests, a dead wake-word UI path, and a missing `docs/ATTRIBUTION.md` referenced by its package.json — evidence of drift, not a template to emulate in the fresh build.
- `docs/Mark-LIV-LICENSE.txt` (Mark LIV — JARVIS, © FatihMakes, **CC BY-NC 4.0**): non-commercial — the separately-delivered Mark-LIV asset must be used under those terms.
- No repository or prototype file was modified during this audit; clones are pristine; the previous YORU build was read-only.
- "No comments in code" policy applies to future YORU work; this audit doc intentionally leans on evidence paths.

---

## 7. FINAL DONOR MATRIX (build-phase decision record)

> **Purpose.** For every audited source, decide per YORU subsystem what the fresh build may do with it. Decisions are **COPY** (vendor source into `D:\YORU\app` with documented origin/license/reason), **ADAPT** (modify and vendor), **REIMPLEMENT** (write fresh code that realizes the same idea/pattern — architecture/UX/algorithm, not the expression), **REFERENCE ONLY** (study only; nothing carries over), or **REJECT** (do not use, even as a pattern).
>
> **Overriding rules.** (§ Architecture Rule) New YORU is a from-scratch implementation in `D:\YORU\app` only; every borrowed component records origin + license + reason. License caps: **Copy/Adapt requires a permissive license (Apache-2.0 / MIT / user-granted)**. vierisid/jarvis (RSALv2-based) and Mark-LIV (CC BY-NC) can never be Copy/Adapt → pattern re-implementation or reference only. friday is usable per **user-reported direct permission** only (no repo LICENSE — do not claim MIT).
>
> **YORU subsystem map.** S1 Agent core/orchestrator · S2 Tool & plugin framework · S3 Permission/approval/audit · S4 Memory & persistence · S5 Voice input (STT/VAD/wake/PTT) · S6 Voice output (TTS/speaker) · S7 Avatar/HUD/ISLAND UI · S8 Desktop control & settings actions · S9 Search/weather/info actions · S10 Remote control/dashboard · S11 Automation (briefing/monitors/proactive) · S12 Security hardening · S13 Tests/docs.

| Source | YORU subsystem | Decision | Reasoning |
|---|---|---|---|
| **OpenJarvis** (Apache-2.0) | S1 orchestrator/agent-loop | **ADAPT** | License-clean, most complete Python scaffolding: registry-driven loops, capability model, memory, MCP client. Vendor selected `core/` modules with attribution. |
| OpenJarvis | S2 tool framework | **ADAPT** | Register/schema/skill conventions (agentskills.io). Keep YORU's own naming/boundaries. |
| OpenJarvis | S3 RBAC/capabilities | **ADAPT** | `security/capabilities` model is the strongest permissive source for YORU's permission model. |
| OpenJarvis | S4 memory | **ADAPT** | Facts + vectors + persona store; combine with YORU prototype's privacy-by-persistence. |
| OpenJarvis | S5–S6 voice | **REFERENCE ONLY** | Uses faster-whisper/Kokoro; YORU's voice plan differs (see handy/OmniVoice/Mark-LIV ideas). |
| OpenJarvis | S13 | **ADAPT** | Lap test patterns; YORU writes its own suite. |
| **handy** (MIT) | S5 voice input | **ADAPT** | Audio toolkit, VAD, push-to-talk, Windows reliable paste — MIT, rebrand. Strongest local-STT donor. |
| handy | S8 paste/type/clipboard | **ADAPT** | Clipboard/inject reliability ideas. |
| handy | S10 remote signal | **REIMPLEMENT** | `signal_handle` concept (remote trigger) is simple enough to rebuild. |
| **OmniVoice** (Apache-2.0) | S6 TTS/voice design | **ADAPT** (as isolated sidecar) | SOTA cloning/design; run as a Python subprocess sidecar with consent rules respected. |
| **jarvis-demo** (MIT) | S1 build-orchestration | **REFERENCE ONLY** | Voice→Claude Code idea overlaps YORU's scoped automation; primitives schema is useful. |
| jarvis-demo | S7 visualization | **REFERENCE ONLY** | three.js Sentinel concept; YORU picks its own HUD. |
| **ultron** (MIT) | S7 HUD inspiration | **REFERENCE ONLY** | Orb conception only; UI licenses fine but YORU needs its own visual identity. |
| **agency-agents** (MIT) | S2 skills/personas | **ADAPT** | Markdown personality/skill-lib convention; seed content with attribution. |
| **vierisid/jarvis** (RSALv2-based) | S8 Win32 UIA/OCR/awareness | **REIMPLEMENT** | License forbids vendoring. Rebuild the *blueprint* (UIA tree, screenshots, OCR loop, awareness) in YORU's stack. |
| vierisid/jarvis | S3 authority gating | **REFERENCE ONLY** | Study approval+audit design; write own. |
| vierisid/jarvis | S5 wake word | **REIMPLEMENT** | openwakeword idea is standard; write our own gate (see Mark-LIV's lazy-load pattern). |
| **friday** (user-granted; no MIT) | S1–S13 | **REFERENCE ONLY / selective ADAPT w/ permission** | Sagar Tamang's direct permission covers use; repo has no LICENSE — incorporate only with PROVENANCE.json record. Patterns (MCP+LiveKit bridge) informative; YORU's realtime path may differ. |
| **Previous YORU prototype** (user's own) | S1 bounded ReAct + sticky denial | **REIMPLEMENT** | Fresh implementation of the proven loop; do not lift structure (Architecture Rule). |
| " | S3 approval+audit gate | **REIMPLEMENT** | Argument-manifest boundary, approve-before-mutate, audit trail. |
| " | S4 store/retrieval | **REIMPLEMENT** | Atomic tmp+rename, 0600, never-persist-messages, reminders semantics. |
| " | S8 scoped project harness (AURORA) | **REIMPLEMENT** | Path jail + SHA-256 checkpointed writes + "an edit is not a verified build". |
| " | S9 no-key search/weather | **REIMPLEMENT** | DuckDuckGo-HTML + Open-Meteo patterns from own prior work. |
| " | S7 island states | **REIMPLEMENT** | Island UX incl. inline permission; keep ONE state vocabulary. |
| " | S13 | **REIMPLEMENT** | One harness per surface; fix the stale-test drift (was a prototype failure). |
| **Mark-LIV** (CC BY-NC) | S5 voice pipeline (echo tail, EchoGuard, wake/PTT gating) | **REIMPLEMENT** | Non-commercial license → no vendoring. Rebuild measured-latency echo tail, band-energy echo classification, mic gating in YORU's own stack. |
| " | S6 render path + viseme mouth | **REIMPLEMENT** | Transcript+audio fused visemes, play-cursor timeline, frame-rate-independent smoothing — implement fresh. |
| " | S1 session resumption | **REIMPLEMENT** | RAM-only handles + voluntary reconnect — standard Live-API pattern. |
| " | S2 discovery + scheduling channels | **REIMPLEMENT** | Auto-discovery with per-file isolation; WHEN_IDLE/SILENT/INTERRUPT result scheduling. |
| " | S3 forged-proof confirm gate / undo | **REIMPLEMENT** | UI-issued token the model cannot forge + undo-closure stack — rebuild. |
| " | S4 two-tier memory + key index | **REIMPLEMENT** | Core block + [ALSO REMEMBERED] index + lexical recall. |
| " | S7 software-rendered avatar | **REFERENCE ONLY** | QPainter head is strong, but YORU's Island identity differs; study only. |
| " | S8 device probing-by-measurement | **REIMPLEMENT** | Open-real-stream + transport-moves-audio probes; name-based config. |
| " | S10 dashboard | **REFERENCE ONLY** | TLS + AES + one-time pairing is instructive; build YORU's own (credentials policy differs). |
| " | S11 automation engines | **REIMPLEMENT** | Two-phase briefing, proactive w/ speech-respect gates, monitors. |
| " | S13 | **REJECT/REFERENCE** | No test suite in Mark-LIV to copy; YORU writes its own. |

**Net shape for `D:\YORU\app` (from matrix):** permissive-license code (OpenJarvis/handy/OmniVoice/jarvis-demo/ultron/agency-agents + own prototype ideas) may be **adapted/re-implemented**; restricted-license sources (vierisid/jarvis, Mark-LIV, friday-without-repo-license) contribute **patterns only, re-written fresh**. Zero verbatim copying from CC BY-NC / RSALv2 material.

**Stop point:** This completes the donor/reference audit of all ten sources. The `D:\YORU\app` directory remains empty until the user approves this matrix and the build plan.