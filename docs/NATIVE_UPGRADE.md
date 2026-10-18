# Current mobile update

The compact toolbar, wake-listener fix and expanded mobile mirroring/control setup are documented in [MOBILE.md](MOBILE.md). The original release notes below describe the earlier foundation.

# KAIRO native voice upgrade — 22 September 2026

## Start on Windows

This verified upgrade is delivered in this task's `outputs/KAIRO` folder. Installation into `D:\KAIRO\app` was not performed because write access was not granted. You can run the delivered copy now. To replace the older installed application, close KAIRO, then double-click `Install-To-D-KAIRO.cmd` in the delivered folder. It backs up application files under `D:\KAIRO\backup-before-native-<timestamp>`, copies the upgrade and installs its dependencies. It does not copy or replace `%APPDATA%\KAIRO` or AURORA. The installer itself has not been run against your installation.

1. Keep the whole KAIRO folder together. Install Python 3.12 (64-bit) and Microsoft Edge WebView2 Runtime if absent. The runtime embeds the UI in a native window; an Edge/Chrome browser window is not required.
2. Double-click `Setup-KAIRO.cmd` once. This installs the desktop and companion dependencies into `.venv`. The compiled full-panel UI is included; Node is only needed when editing it.
3. Keep your existing `GEMINI_API_KEY`/`GOOGLE_API_KEY` environment variable, or `KAIRO_CREDENTIALS_FILE` pointing to your local JSON credentials. Never put credentials in the UI or project source. Existing `%APPDATA%\KAIRO` configuration, AURORA project allowlists, journal and memory are reused, not replaced.
4. Double-click `Start-KAIRO.cmd`. It opens the full-panel native KAIRO window and starts its authenticated loopback backend automatically. No URL needs copying. `.venv\Scripts\KAIRO.exe` is also the generated GUI entry point after setup; keep it with its environment. This is not yet a standalone distributable executable or installer.
5. In Settings, retain Gemini Live and the configured model. Click **Show audio devices** to inspect actual Windows devices, select an output if needed, then **Test Windows voice output** for a short tone.
6. Click **Enable wake listening** to explicitly opt in each launch. Say **Hey Kairo**. KAIRO foregrounds and asks Gemini for a brief greeting, then keeps the same microphone/session open across turns. Speak over a response to interrupt it. Headphones are recommended because acoustic echo cancellation has not been implemented.
7. Say **Kairo, go to sleep** or click **Sleep**. KAIRO minimizes; a small always-on-top listening indicator remains with **Disable listening** and **Open KAIRO** controls. **Stop** or **Disable listening** closes active audio and wake listening. Closing the main KAIRO window exits the backend and listeners.

Optional clap wake requires **two** sharp claps separated by 0.18–0.8 seconds. Stay quiet for the first three seconds of wake listening for calibration. Adjust the threshold while listening is disabled. Sustained noise, insufficient quiet between peaks, low confidence speech and wakes during the five-second cooldown are rejected. Wake speech uses Windows' local English (US) speech engine/default microphone; the clap and Gemini adapters honor `brain.input_device`. For consistent behavior set the Windows default microphone to the intended input. Calibration and recognition accuracy in the actual room still need user validation.

## Audio and recovery

The inspected saved configuration selected `Kreo Owl Audio` as output. Windows reports that device as input-only. The adapter now routes a legacy input-only selection to the actual Windows default output and reports the correction. Explicit valid outputs remain selected; Settings saves a device name plus host API rather than a guessed numeric device ID. A saved explicit output that disappears produces an error.

Gemini output stays native mono signed PCM16 at 24,000 Hz. Playback failures signal the session instead of silently disappearing. Server interruption clears playback without releasing microphone capture. Stop releases both. A mid-turn disconnect stops the conversation and disables listening; no audio, prompt or action is automatically replayed. Review activity and enable listening again for a fresh session. Seamless reconnection with context across an unexpected disconnect is not implemented. Context is retained across normal active turns within the same live session.

## LAN companion foundation

Nothing listens on LAN by default. No public tunnel, firewall change, router configuration or port forwarding is performed. The local desktop bridge stays bound to 127.0.0.1. Companion traffic uses a separate TLS-only server bound to one explicit RFC1918 IPv4 address.

Add a `companion` object to your existing local `%APPDATA%\KAIRO\config.json` (retain all other settings):

```json
"companion": {
  "address": "192.168.1.50",
  "port": 8766,
  "certfile": "C:/KairoCertificates/lan-cert.pem",
  "keyfile": "C:/KairoCertificates/lan-key.pem"
}
```

Replace the sample address with this PC's actual LAN address. Provision a certificate with that IP in its subject alternative names and a CA trusted by your phone. Keep the private key local and access-restricted. Certificate provisioning/trust installation is intentionally not automated; do not bypass TLS certificate validation. If Windows Firewall blocks access, allow only the chosen port on your private network/local subnet. Do not expose it to the public network.

In Settings → Mobile companion foundation, start the secure listener, choose permissions, and create a pairing code. Open `https://<your-LAN-address>:8766/` on the phone and enter the code. The code lasts two minutes, allows at most five attempts, and is single-use. Sessions last one hour, remain only in memory, and are immediately revocable on the PC. Closing the phone page forgets its local token; **Revoke all and stop companion** invalidates sessions and closes the listener. Restarting KAIRO also invalidates sessions.

Implemented: scoped touchpad movement, media/volume keys, individually approved left-clicks and ASCII typing, and individually approved screen snapshots. Clicks/typing bind to the original foreground window identity; a changed/unrestorable target fails closed. No Enter, arbitrary hotkeys, shell execution or remote approval endpoint is provided. Command sequence numbers prevent replay. Revocation is checked again after PC approval.

Remaining: QR presentation, certificate setup wizard, continuous mirroring/video transport, Unicode keyboard input, app/window controls, per-device session management UI, and full phone/browser/hardware end-to-end validation. The `windows` scope is reserved; its actions fail closed. Use the implemented code-pairing flow rather than a QR shortcut.

## Validation and boundaries

- All 57 Python regression tests pass, including the existing permission/audit/provider/integration tests plus wake, continuous-session, sleep, false-wake, native backend lifecycle, audio format/interruption/failure, pairing expiry/revocation/scope/replay tests.
- Production UI build and TypeScript checks pass. Native WebView2 smoke test opened the built full-panel UI, authenticated to the backend and exited successfully, with no microphone capture.
- Actual Windows default output accepted and played a silent 24 kHz PCM buffer. A live Gemini text-triggered probe returned 205,442 bytes of native audio and completed playback. This verifies delivery to the Windows output API; human audibility was not independently confirmed.
- Real spoken wake, room-level clap accuracy, live microphone multi-turn/barge-in and phone TLS pairing still require hands-on acceptance checks. Automated tests cover their policy/session boundaries, not acoustic performance.
- No Mark-LIV source was imported. Existing AURORA, permissions, audit journal, identity and attribution files are retained. Companion actions use the existing PC-side authority and audit journal.

To rebuild or test from this folder:

```powershell
.venv\Scripts\python.exe -m pip install ".[native,companion,test]"
.venv\Scripts\python.exe -m pytest -q
cd ui
npm ci
npm run build
cd ..
.venv\Scripts\python.exe scripts/native_smoke.py
```

The smoke test opens and closes the UI automatically and keeps microphone listening disabled. Historical architecture/research notes describe earlier interfaces; this file is the current native startup and limitation reference.
