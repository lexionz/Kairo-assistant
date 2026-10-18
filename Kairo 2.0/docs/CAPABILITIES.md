# KAIRO capability and interaction boundaries

KAIRO's interaction policy lives in `src/kairo/interaction.py`. `InteractionBrain`
is the interface for a future separately trained interaction model. The current
implementation is deterministic policy, not a trained custom model. Compatible
reasoning and Gemini Live remain separate provider implementations. Provider
identity must be disclosed truthfully when asked.

## Selecting and acquiring capabilities

`Tools` is the executable registry. Provider schemas are generated from its current
contents. `capability_catalog` ranks tools for a task and includes input schemas,
approval requirements, and persisted adapter metadata. Missing tool requests return
a discovery hint rather than implying that execution happened.

When needed, the planner calls `capability_discover` to search public official
documentation, reads primary sources, and decides whether an existing tool or a new
adapter can fulfill the task. Discovery results are untrusted evidence.

The implemented acquisition workflow is:

1. `capability_propose`: construct a declarative adapter for a fixed public HTTPS
   document. No query strings, credentials, executable code, or arbitrary imports.
2. `capability_test`: fetch through the existing restricted research client; require
   nonempty text and record time and content hash.
3. `capability_activate`: obtain an exact owner approval, reject stale/changed
   tests, then register the adapter.
4. Call its dynamically registered tool, or `capability_read` during an existing
   Gemini Live session. This stable tool avoids changing the Live session schema.

Metadata is atomically persisted to `capabilities.json` in KAIRO's data directory.
On restart it is a proposal, never a new grant of authority. Retest and reactivate.
No raw page bodies, API keys, or user conversations are persisted by this registry.

This is a working read-only adapter builder, not an arbitrary plugin/code installer.
Discovery for other integrations returns evidence and implementation guidance.
Executable adapters still require reviewed source, tests, and explicit permission
before connecting high-impact capabilities. Do not claim those are installed.

## Execution and verification

`task_plan` emits a plan and intended verification criteria. Both provider paths use
the same audited tool boundary. Actions emit act/observe events. Failures return to
the planner for changed-input repair; a tool is blocked after three consecutive
failures. There is no automatic retry of a mutating action. Existing per-task denial,
bounded rounds/source budgets, cancellation, exact edit hashes, checkpoints, and
project verification remain in place. Live turns emit source and project evidence.

Public HTTPS reading/search runs without approval. Every destination/redirect is
checked against private/special networks and TLS is pinned to the validated DNS
address. The existing byte, source-count, timeout and PDF extraction limits remain.
Fetched material never authorizes an action. A running threaded fetch may take its
network timeout to end after cancellation; its cancelled result is not acted on.

Project edits, executable project commands, undo, durable memory, MCP tools and
adapter activation still require approval. No software-installation, credential
entry, purchase, destructive-system or security-change tool is added. Supporting
those later must preserve explicit approval and least privilege.

## Wake and UI

The first wake-enable action in Settings saves local consent, clap choice and
threshold in `wake-consent.json`. Normal native startup restores only that explicit
consent. Disabling listening, including from the privacy indicator, clears it.
Application shutdown releases audio without revoking the saved user preference.

The existing Hey Kairo / calibrated two-clap wake opens the UI and starts continuous
Gemini Live conversation. Barge-in interrupts playback without ending capture.
The sleep phrase returns to local wake-only listening. Wake is currently supported
through Gemini Live; compatible text providers remain usable through typed input.

The redesigned scene reads actual state and recent audio amplitude from the backend.
Standby is still; active rotation/color/intensity reflect listening, thinking,
speaking, acting, errors and approvals. Settings/mobile/conversation panels appear
only when opened; action approval appears when required. A contextual menu and a
small privacy indicator remain available. No permanent top mic/stop/sleep toolbar.

The source UI must be built into `ui/out` before `Start-KAIRO.cmd` launches it.
The launcher does not serve the TypeScript source directly.

## Reference consulted

Google Live API reference: https://ai.google.dev/api/live
Session management: https://ai.google.dev/gemini-api/docs/live-api/session-management
The existing configured model was preserved; no provider or model was silently changed.

## Plugin/MCP integration update — September 24

The contextual Tools & plugins panel manages reviewed plugin packages and actual
MCP connections. `plugins.py` provides Python documentation, MCP documentation,
and local utilities packages. `integrations.py` owns connection lifetime, starts
the bundled `local_mcp.py` read-only server on a reserved loopback socket, and
removes its tools on disconnect. Both SSE and Streamable HTTP are supported.

`integration_discover` only reads manifests. `integration_connect` requires owner
review for model requests; the local UI lets the user select exact tools. Custom
server annotations never exempt action approval. Only utilities hosted by the
known bundled server receive read-only treatment. `integration_call` dynamically
dispatches through the same Tools authority boundary during existing Live sessions.
No downloaded executable code is loaded. Local runtime connections are session-scoped.
