# KAIRO architecture decision — 2026-09-20

## Current integration amendment

The current user request replaces the original Tk presence as the default with the MIT ULTRON scene adapted into KAIRO's static web UI. `web.py` exposes an authenticated loopback-only event/command bridge. Gemini Live is the selected default brain and native voice provider, independently implemented in `gemini_live.py` and `live_audio.py` from verified protocol/configuration facts. `docs/GEMINI_LIVE_PARITY.md` specifies exact settings and deliberate compatibility differences. The compatible HTTP provider and Windows voice are optional, explicitly selected alternatives; there is no automatic substitution. `docs/INTEGRATION_MAP.md` governs current donor integration. Earlier interface and push-to-talk-only architecture descriptions below describe the preceding implementation. Exact action approval, audit, memory and AURORA boundaries continue to apply.

Status: accepted for this implementation under the user's instruction to reconcile research and continue the fresh build. This supersedes the earlier terminal-only sequencing, not the preserved research. No old YORU or LUNARIS source is used as a foundation. D:/YORU/app is preserved independently, including its later Python voice work.

## Reconciliation

D:/YORU/docs/UPSTREAM_AUDIT.md exists and contains ten donor sources and a final matrix. Its assertion that app is empty is stale: app contains a Python voice implementation and a status claiming 35 tests. That claim is historical, not verification of KAIRO. No APEX section was present. The source and license inventory was checked against the eight local clones; APEX is added in docs/APEX_RESEARCH.md. Mark-LIV remains non-commercial reference material, not vendored code. FRIDAY has no repository license; user-reported permission is recorded without inventing a general license.

## Boundaries

KAIRO uses a small Python runtime with independent contracts. The event stream is the only UI connection. The core has no desktop-widget dependencies.

| Module | Responsibility |
| --- | --- |
| contracts | Typed events, tool declarations, bounded argument validation |
| authority | Expiring, single-use approval bound to exact prepared action and task |
| journal | SQLite audit, explicit memories, checkpoint metadata; no raw conversation persistence |
| workspace | Approved project paths, snapshots, exact-content edits, fixed command aliases |
| tools | Registry and prepared-action boundary; errors become observations |
| inference | Replaceable async brain; compatible local or HTTPS endpoints; no built-in fake brain |
| runtime | Bounded plan/act/observe/retry loop, sticky denials, cancellation and evidence report |
| voice | Replaceable STT/TTS contract and Windows Speech subprocess adapter |
| mcp_link | Explicit connection, loopback endpoint, tool allowlist and per-call approval |
| research | On-demand web/docs/repository/paper retrieval, dated evidence, claim ledger, contradiction detection and durable knowledge proposals |
| desktop | Compact top-center animated core, visible mic, exact approval review and hidden controls |

One coordinator is sufficient for the baseline. Specialist roles can later receive a subset of its capabilities and budget. Do not add autonomous subagents, scheduled jobs, screen surveillance or self-modifying authority to make the architecture look more elaborate. Learning means inspectable traces and evaluations for now, not an untested learning claim.

## First-class research contract

The coordinator researches when context is missing, when a claim is time-sensitive, when an error requires documentation, or when the user requests evidence. Research is not a background crawl or an internet dump. Each task has bounded retrieval rounds, page bytes, result counts and context. A research specialist gets read-only network capabilities and the task's budget, never file-write or execution privileges. The coordinator may delegate to this bounded contract and receives a sourced report, not another authority-bearing prompt.

Sources carry canonical URL, title, publisher host, retrieved UTC time, available published/modified metadata, content hash, source type and excerpt. Search results and paper metadata are discovery records; they do not certify full-text claims. Documentation and repository code are fetched on demand. Repository source URLs should pin commit revisions for reproducibility. HTTP date headers are freshness signals, not proof of factual currency.

Claims are registered with a proposition key, asserted value and exact source-supported excerpts. Distinct values for the same proposition create a visible conflict, never silently overwrite one another. Two independent publisher domains are a minimum evidence signal, not automatic truth. A claim with only one source, stale retrieval, metadata-only evidence, or a conflict remains qualified. Semantic contradiction discovery beyond explicit proposition/value registration requires the brain's judgment and is not represented as infallible.

Only user-approved durable knowledge is persisted, with citations, verification state, expiry and a review date. Raw web pages and transcripts are not long-term memory. Expired knowledge must be rechecked. Source text cannot grant permissions, redefine tools, or request secrets. Network fetch validates and pins public DNS addresses, limits redirects/body sizes/time, rejects credentials, loopback/private/link-local destinations, and only uses HTTPS port 443. Every task's research evidence can be inspected independently of model prose.

## Runtime contract

Push to talk opens a bounded Windows recognition session. Release closes capture and returns a transcript. The mic is off during inference, tool execution and speech output. Stop cancels pending approvals, HTTP requests and the owned speech/command process. Wake-word and acoustic barge-in need dedicated opt-in implementations and are not enabled. This fixes the always-monitoring and echo limitations recorded in the later D: voice prototype.

User text -> RAM conversation + selected explicit memory -> model tool request -> validate -> prepare exact operation -> review/permission -> execute -> observe -> retry or repair -> verification evidence -> speech. No action is allowed merely because model text says approved. File content, tools and memory are untrusted data, not grants of authority.

Project reads require an approved configured root. Edits require a previously read hash, full diff review and one-time approval; a checkpoint is saved before mutation. Commands are fixed executable/argument tuples chosen by the owner, never a model-supplied shell string. Running project code is permission-scoped, NOT an OS sandbox. Processes inherit a reduced environment, excluding model keys. A build command needs approval even if it has a familiar name. AURORA production is D:/AURORA/AuroraUE5 per its own README; source checks and engine builds remain distinct.

Verification is structured evidence outside model prose. A successful write verifies bytes only. A passing command verifies only that command at the current project revision. Any subsequent edit invalidates prior command evidence. Stop never claims to undo earlier actions.

## Interface

Original small near-black circular core with a broken halo; pearl idle, jade listening, moving pale arcs for thinking, amber acting/approval, blue speech. Not a transplanted LUNARIS pill or a full-screen APEX constellation. Controls and task text live in a hidden panel. Permissions expose full before/after differences and exact command arguments. Motion comes from actual runtime events; a test preview is never presented as a completed action.

## Packaging and location

Staging and reviewable deliverables are under this task's outputs/KAIRO. The intended installation is D:/KAIRO/app. Create it without moving or editing D:/YORU. Research snapshots and source pointers go under D:/KAIRO/docs. Use KAIRO for package, imports, config, state, logs, tests and commands. Historical YORU names remain only in explicit provenance/history.

## Acceptance

Tests must execute real scoped file writes, denial, stale approval, command failure, repair, cancellation, evidence invalidation, persistence and a real protocol handshake. Scripted model responses are test fixtures only. Test actual Windows speech using generated WAV separately from live microphone validation. No configured provider means the full live conversation remains blocked and is reported honestly. Hardware and live-model checks are not replaced with animations.
