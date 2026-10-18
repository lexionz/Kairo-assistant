# KAIRO provenance

## Current UI integration (2026-09-20)

The UI now adapts Sagar Tamang's MIT-licensed ULTRON `lib/orbScene.ts`, `lib/handTracker.ts`, visual CSS and component scaffold from the uploaded archive. Copyright (c) 2026 Sagar Tamang. The complete license is preserved in `reference-licenses/ultron-by-sagar-builds-LICENSE`. Changes: KAIRO identity, real assistant controls and events, input-safe shortcuts, WebGL fallback, motion preferences, layout and authenticated runtime connection. Archive hashes and source-entry hashes are recorded in ARCHIVE_PROVENANCE.json. The earlier no-copied-UI statement below describes the preceding build and is superseded for these named files only.

Gemini Live integration is independently written against the public google-genai SDK interface. Model identifiers, protocol rates and configuration values were verified from Mark-LIV's active path as factual interoperability requirements; no Mark-LIV implementation or prompts are included. OmniVoice integration is an independent optional subprocess adapter; model code/weights are not bundled. The Gemini Live provider uses Gemini's native audio output, not this optional sidecar.

## Previous build provenance

New application modules were independently written for this build. No code or artwork was copied from LUNARIS, the old Electron YORU prototype, the later D:/YORU Python prototype, Mark-LIV, vierisid/jarvis, or the proprietary APEX Humanoid. Historical source names remain in research records only.

Research references: OpenJarvis (modular engines/agents/tools/memory), Handy (explicit voice capture and local STT patterns), OmniVoice (future replaceable voice engine), Aidos/jarvis-demo (voice-to-engineering harness), Sagar Tamang FRIDAY (MCP/voice separation), Ultron (visual inspiration), agency-agents (specialist role conventions), vierisid/jarvis and FatihMakes Mark-LIV (restricted-license reference only), prior user builds (failure lessons), Reznikov APEX (visible actions and interface/brain separation).

The inherited ten-source audit and its notices are preserved as historical evidence. The audit's copying permissions are not a blanket license for all sources. FRIDAY has no repository LICENSE at the inspected commit; user-reported direct permission is recorded without claiming MIT. Mark-LIV carries CC BY-NC 4.0; vierisid/jarvis is source-available under its own terms. APEX-UI is MIT; the Humanoid has separate tiered terms and was not acquired. No protected voices, character identities or artwork are included.

Runtime dependencies retain their own package licenses (httpx, MCP Python SDK, pdfplumber and transitive dependencies). Windows System.Speech and Python/Tk are installed platform components. No neural model weights are bundled. Research pages remain third-party material; store only needed evidence and citations, not entire copyrighted collections.
