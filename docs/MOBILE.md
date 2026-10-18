# Mobile screen view and PC controls

Open **Mobile** in KAIRO's small top-right toolbar. This is a phone-browser companion for controlling your Windows PC, not an app that remotely controls Android or iOS.

## First connection

1. Connect the PC and phone to the same private Wi-Fi/LAN.
2. Select the PC's listed LAN address and click **Prepare secure connection**. KAIRO creates a local server certificate and a public phone trust certificate valid for 30 days. It does not change firewall rules or install trust automatically.
3. Click **Save phone trust certificate**, transfer that public `KAIRO-Phone-Trust.cer` file to your phone, and install it as a trusted CA through your phone's certificate/profile settings. On iOS, certificate trust may also need to be explicitly enabled after installing the profile. Never transfer `server-key.pem` or bypass certificate warnings. The certificate's file location and SHA-256 fingerprint are shown in KAIRO.
4. Select only the permissions you want: Live screen, Touchpad, Keyboard, Media and volume, or Open apps and windows.
5. Click **Start mobile connection**, then **Create pairing code**. Open the displayed HTTPS address on the phone and enter the code. The code is single-use, expires after two minutes and locks after five failed attempts.
6. If the phone cannot connect, check that it is on the same network and that Windows Firewall allows this application's port 8766 on the private/local subnet. KAIRO does not open a firewall port or configure public exposure for you.

Trust setup is a one-time manual phone step until the certificate expires or the PC address changes. Devices managed by an organization may prohibit user-installed CAs. You can instead supply an appropriately trusted certificate using the existing local companion configuration.

## Controls

- **Start live view** asks for approval on the PC and streams compressed images of the primary screen, including a cursor overlay, at up to two frames per second for five minutes. This is low-frame-rate mirroring, not video/audio streaming. There is a visible stop-sharing indicator even when the main KAIRO window is minimized.
- **Stop view** stops sharing; **Snapshot** requests one approved image.
- Drag the **Touchpad** to move the Windows pointer. Left clicks require PC approval and remain bound to the reviewed window and coordinates.
- **Keyboard** sends bounded printable ASCII text to the reviewed foreground app after PC approval. Enter, arbitrary hotkeys and Unicode input are not supported.
- **Media & volume** offers play/pause, previous/next, mute and volume up/down.
- **Open apps** lists visible windows. Open/focus, minimize, maximize and close operations require PC approval. It controls already-running apps; arbitrary app launch or shell commands are not exposed.
- **Disconnect** on the phone revokes that session. **Disconnect all devices** on KAIRO revokes every token and closes the listener. Phone sessions expire after one hour. Backgrounding the phone page stops its live view.

The PC must remain awake. This does not wake a suspended or powered-off PC. Lock-screen/elevated-window control, multiple-monitor selection, full-motion video, remote audio and native Android/iOS packaging are not implemented.

## Verification

64 regression tests pass, including encrypted HTTPS pairing/frame requests using a trusted test certificate, mirror approval, denial, expiry, stop, revocation during capture and window permission checks. The phone layout was verified at a 374-pixel viewport without horizontal overflow. The actual native KAIRO toolbar measured 32 pixels high. The corrected Windows wake process reported ready and remained alive for five seconds before the test shut it down.

Physical-phone certificate installation and room-level spoken wake/clap accuracy still need user acceptance testing.
