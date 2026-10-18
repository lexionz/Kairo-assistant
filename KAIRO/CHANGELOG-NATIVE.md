# Compact UI and mobile update

- Replaced the large panel with a 32-pixel control strip; settings and pairing open on demand.
- Fixed the Windows wake recognizer constructor: language is now passed as CultureInfo rather than a recognizer ID. Startup was verified on the actual microphone.
- Added guided LAN/TLS setup, mobile live screen viewing at up to 2 fps, persistent Stop sharing, window controls, and session revocation from the phone.
- 64 tests pass; production UI and phone-sized layout checks pass. See docs/MOBILE.md for setup and limits.

# Native voice upgrade

- Reused the existing full-panel orb UI in a Windows WebView2 shell with a KAIRO taskbar identity and automatic backend lifecycle.
- Replaced the primary chat, transcript/evidence feed, Send and manual Talk controls with voice presence, Stop, settings and approval controls.
- Added session-only opt-in local wake phrase recognition and calibrated conservative two-clap detection, sleep/minimize and a disableable listening indicator.
- Kept active Gemini microphone capture across turns; server barge-in interrupts playback without terminating capture. Sleep ends active audio and returns to local wake listening.
- Corrected legacy input-only output-device selection, retained native 24 kHz PCM, exposed output selection/test, and surfaced playback failures. Mid-turn disconnects fail closed without replay.
- Added separately enabled TLS LAN companion, short-lived code pairing, scoped/revocable sessions, replay protection, bounded controls and local approval/audit.
- Added regression tests and a native-window smoke probe. See `docs/NATIVE_UPGRADE.md` for setup, validation evidence and remaining work.
