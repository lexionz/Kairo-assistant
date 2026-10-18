import asyncio

import collections

import hmac

import json

import mimetypes

import secrets

import threading

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pathlib import Path

from urllib.parse import parse_qs, urlsplit





class Bridge:

    def __init__(self, application, loop):

        self.app, self.loop = application, loop

        self.token = secrets.token_urlsafe(32)

        self.events = collections.deque(maxlen=256)

        self.sequence = 0

        self.state = {"state": "idle", "text": "Ready · microphone off"}

        self.presence = "disabled"
        self.audio = 0
        self.audio_at = 0
        self.review = None

        self.lock = threading.Lock()

        application.events.subscribe(self.record)



    def record(self, event):

        with self.lock:

            self.sequence += 1

            self.events.append({"id": self.sequence, "kind": event.kind, "payload": event.payload})

            if event.kind == "presence":
                self.presence = event.payload["mode"]
            if event.kind == "audio":
                self.audio = event.payload.get("level", 0)
                self.audio_at = __import__("time").monotonic()
            if event.kind == "state":

                self.state = event.payload

            if event.kind == "approval":

                self.review = event.payload

            if event.kind == "approval_closed":
                self.review = None



    def read(self, after):

        with self.lock:

            return {"cursor": self.sequence, "presence": self.presence, "audio": self.audio if __import__("time").monotonic() - self.audio_at < .5 else 0, "state": self.state, "approval": self.review, "mirroring": self.app.companion.mirroring(),

                    "events": [e for e in self.events if e["id"] > after]}



    async def command(self, data):

        action = data.get("action")

        if action == "companion_addresses":

            from kairo.companion_setup import local_addresses

            return {"addresses": local_addresses()}

        elif action == "companion_prepare":

            if self.app.companion_server:

                raise ValueError("Stop the companion before changing its setup")

            from kairo.companion_setup import prepare

            result = await asyncio.to_thread(prepare, self.app.directory, data.get("address"))

            self.app.config["companion"] = {k:result[k] for k in ("address","port","certfile","keyfile")}

            temporary = self.app.config_file.with_suffix(".tmp")

            temporary.write_text(json.dumps(self.app.config, indent=2), encoding="utf-8")

            temporary.replace(self.app.config_file)

            return {k:result[k] for k in ("address","port","trust_file","fingerprint","expires","certificate")}

        elif action == "companion_start":

            if self.app.companion_server:

                raise ValueError("Companion is already running")

            from kairo.companion_server import start_companion

            config = self.app.config.get("companion", {})

            if not all(config.get(k) for k in ("address", "port", "certfile", "keyfile")):

                raise ValueError("Configure a LAN address and trusted TLS certificate in the local companion settings first")

            self.app.companion_server = start_companion(self.app.companion, self.loop, **{k: config[k] for k in ("address", "port", "certfile", "keyfile")})

            return {"ok": True, "address": f'https://{config["address"]}:{config["port"]}'}

        elif action == "companion_mirror_stop":

            self.app.companion.stop_mirroring()

        elif action == "companion_pair":

            if not self.app.companion_server:

                raise ValueError("Start the secure companion listener first")

            return self.app.companion.issue(data.get("scopes"))

        elif action == "companion_revoke":

            self.app.companion.revoke()

            if self.app.companion_server:

                await asyncio.to_thread(self.app.companion_server.shutdown)

                self.app.companion_server.server_close()

                self.app.companion_server = None

        elif action in {"wake_enable", "wake_disable", "sleep"}:

            presence = getattr(self.app, "presence", None)

            if not presence:

                raise ValueError("Start the native KAIRO app to use wake listening")

            if action == "wake_enable":

                if type(data.get("claps", False)) is not bool:

                    raise ValueError("Invalid clap setting")

                await presence.enable(data.get("claps", False), float(data.get("threshold", .35)))
                presence.remember_consent(True)

            elif action == "sleep":

                await presence.sleep()

            else:

                presence.remember_consent(False)
                await presence.disable()

        elif action in {"request", "listen"}:

            if self.app.turn:

                raise ValueError("A task is active; stop it before starting another")

            text = data.get("text") if action == "request" else None

            if action == "request" and (not isinstance(text, str) or not 1 <= len(text.strip()) <= 12000):

                raise ValueError("Enter a request of 1–12000 characters")

            asyncio.create_task(self.app.request(text))

            await asyncio.sleep(0)

        elif action == "release":

            self.app.release()

        elif action == "audio_devices":

            import sounddevice as sd

            return {"devices": [{"id": i, "name": d["name"], "hostapi": sd.query_hostapis(d["hostapi"])["name"], "input": d["max_input_channels"], "output": d["max_output_channels"]} for i, d in enumerate(sd.query_devices())], "default": list(sd.default.device)}

        elif action == "audio_select":

            if self.app.turn:

                raise ValueError("Stop the conversation before changing output")

            import sounddevice as sd

            identity = data.get("device")

            if identity is not None and (type(identity) is not int or identity < 0):

                raise ValueError("Choose a detected output")

            brain = self.app.config["brain"]

            if identity is None:

                brain.pop("output_selector", None)

                brain.pop("output_device", None)

            else:

                device = sd.query_devices(identity, "output")

                sd.check_output_settings(device=identity, samplerate=24000, channels=1, dtype="int16")

                brain["output_selector"] = {"name": device["name"], "hostapi": sd.query_hostapis(device["hostapi"])["name"]}

            temporary = self.app.config_file.with_suffix(".tmp")

            temporary.write_text(json.dumps(self.app.config, indent=2), encoding="utf-8")

            temporary.replace(self.app.config_file)

        elif action == "audio_test":

            if self.app.turn:

                raise ValueError("Stop the conversation before testing output")

            import math

            import struct

            from kairo.live_audio import LiveAudio

            audio = LiveAudio(self.app.events, self.app.config["brain"])

            try:

                pcm = b"".join(struct.pack("<h", int(2500 * math.sin(2 * math.pi * 440 * i / 24000))) for i in range(12000))

                await audio.queue(pcm)

                await audio.drain()

            finally:

                await audio.stop()

        elif action == "stop":

            if getattr(self.app, "presence", None):

                self.app.presence.remember_consent(False)
                await self.app.presence.disable()

            else:

                await self.app.cancel()

            self.app.events.emit("state", state="interrupted", text="Stopped · microphone off; earlier actions remain")

        elif action == "approve":

            if type(data.get("allowed")) is not bool or not self.app.authority.decide(data.get("token"), data.get("task"), data["allowed"]):

                raise ValueError("Approval expired or does not match this task")

        elif action == "snapshot":

            await self.app.snapshot()

        elif action == "forget":

            identity = data.get("id")

            if not isinstance(identity, str) or len(identity) > 100:

                raise ValueError("Invalid memory identifier")

            self.app.journal.forget(identity)

            self.app.journal.record("user", "forget", "completed")

            await self.app.snapshot()

        elif action == "settings":

            endpoint, model = data.get("endpoint"), data.get("model")

            if not isinstance(endpoint, str) or not isinstance(model, str) or len(endpoint) > 2000 or len(model) > 200:

                raise ValueError("Invalid provider settings")

            provider = data.get("provider", "gemini_live")

            voice = data.get("voice", "Charon")

            if provider not in {"gemini_live", "compatible"} or not model.strip() or voice not in {"Charon", "Puck", "Kore", "Fenrir", "Aoede"}:

                raise ValueError("Invalid provider, model or voice")

            if provider == "compatible":

                parsed = urlsplit(endpoint.strip())

                if not parsed.hostname or parsed.username or parsed.password or not (parsed.scheme == "https" or parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "::1"}):

                    raise ValueError("Use HTTPS or an explicit loopback model endpoint")

            await self.app.save_settings(endpoint, model, provider, voice)

        elif action == "config":

            return {"brain": {k: v for k, v in self.app.config["brain"].items() if k in {"provider", "endpoint", "model", "voice"}}, "tools": list(self.app.tools.items)}

        elif action == "integrations":
            return {**self.app.integrations.status(), **self.app.integrations.plugins.catalog(), "catalog": self.app.capabilities.catalog()}
        elif action == "integration_local":
            return await self.app.integrations.start_local()
        elif action == "integration_discover":
            return await self.app.integrations.discover({"url": data.get("url", ""), "transport": data.get("transport", "sse"), "allow": []})
        elif action == "integration_connect":
            if self.app.turn:
                raise ValueError("Finish or interrupt the conversation before changing integrations")
            from kairo.mcp_link import validate_config
            config = validate_config({"url": data.get("url", ""), "transport": data.get("transport", "sse"), "allow": data.get("tools", [])})
            return await self.app.integrations.connect(config)
        elif action == "integration_disconnect":
            if self.app.turn:
                raise ValueError("Interrupt the current task before disconnecting its tools")
            return await self.app.integrations.stop()
        elif action == "plugin_prepare":
            return self.app.integrations.plugins.prepare({"plugin": data.get("plugin", "")})
        elif action == "adapter_test":
            if self.app.turn:
                raise ValueError("Finish the current task before testing an adapter")
            return await self.app.capabilities.test({"name": data.get("name", "")})
        elif action == "adapter_activate":
            if self.app.turn:
                raise ValueError("Finish the current task before activating an adapter")
            prepared = self.app.capabilities.prepare_activation({"name": data.get("name", "")})
            if any(data.get(key) != prepared.get(key) for key in ("url", "sha256", "tested_at")):
                raise ValueError("Adapter changed since review; refresh and review again")
            # This exact local UI action is explicit activation consent. Model calls
            # still pass through Authority via capability_activate.
            result = self.app.capabilities.activate(prepared)
            self.app.journal.record("user", "capability_activate", "completed", {"name": prepared["name"]})
            return result
        elif action == "mcp":

            return await self.app.connect_mcp()

        else:

            raise ValueError("Unknown action")

        return {"ok": True}





def make_server(bridge, static, port=0):

    root = Path(static).resolve()



    class Handler(BaseHTTPRequestHandler):

        def log_message(self, *_):

            pass



        def send(self, status, body, content_type="application/json"):

            if not isinstance(body, bytes):

                body = json.dumps(body, ensure_ascii=False).encode("utf-8")

            self.send_response(status)

            self.send_header("Content-Type", content_type)

            self.send_header("Content-Length", str(len(body)))

            self.send_header("Cache-Control", "no-store")

            self.send_header("X-Content-Type-Options", "nosniff")

            self.send_header("Referrer-Policy", "no-referrer")

            self.send_header("X-Frame-Options", "DENY")

            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' https://cdn.jsdelivr.net; connect-src 'self' https://cdn.jsdelivr.net https://storage.googleapis.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")

            self.end_headers()

            self.wfile.write(body)



        def valid(self, authenticate=False):

            host = f"127.0.0.1:{self.server.server_port}"

            if self.headers.get("Host") != host:

                self.send(403, {"error": "Invalid host"})

                return False

            origin = self.headers.get("Origin")

            if origin is not None and origin != "http://" + host:

                self.send(403, {"error": "Invalid origin"})

                return False

            if authenticate and not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + bridge.token):

                self.send(401, {"error": "Open the link printed by the KAIRO launcher to connect"})

                return False

            return True



        def do_GET(self):

            url = urlsplit(self.path)

            if not self.valid(url.path.startswith("/api/")):

                return

            if url.path == "/api/events":

                try:

                    after = int(parse_qs(url.query).get("after", ["0"])[0])

                except ValueError:

                    self.send(400, {"error": "Invalid event cursor"})

                    return

                self.send(200, bridge.read(after))

                return

            target = (root / (url.path.lstrip("/") or "index.html")).resolve()

            if not target.is_relative_to(root) or not target.is_file():

                self.send(404, {"error": "Not found; build the UI before starting KAIRO"})

                return

            self.send(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")



        def do_POST(self):
            # Consume a bounded body before an early auth/origin rejection. On
            # Windows, closing a socket with unread input can reset the response.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 64000:
                    raise ValueError("Invalid request size")
                self.connection.settimeout(10)
                raw_body = self.rfile.read(length)
                if len(raw_body) != length:
                    raise ValueError("Incomplete request body")
            except (ValueError, OSError):
                self.send(400, {"error": "Invalid or incomplete request body"})
                return

            if not self.valid(True):

                return

            if self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}":

                self.send(403, {"error": "Origin is required"})

                return

            if self.path != "/api/command" or self.headers.get("Content-Type") != "application/json":

                self.send(400, {"error": "Expected a JSON command"})

                return

            try:

                length = int(self.headers.get("Content-Length", "0"))

                if not 0 < length <= 64000:

                    raise ValueError("Invalid request size")

                data = json.loads(raw_body)

                if not isinstance(data, dict):

                    raise ValueError("Expected an object")

                future = asyncio.run_coroutine_threadsafe(bridge.command(data), bridge.loop)

                result = future.result(timeout=45)

                self.send(200, result)

            except (ValueError, TypeError) as exc:

                self.send(400, {"error": str(exc)[:200]})

            except Exception:

                self.send(503, {"error": "KAIRO command unavailable"})



    return ThreadingHTTPServer(("127.0.0.1", port), Handler)





async def serve(application, static, port=0):

    bridge = Bridge(application, asyncio.get_running_loop())

    server = make_server(bridge, static, port)

    worker = threading.Thread(target=server.serve_forever, daemon=True)

    worker.start()

    print(f"KAIRO: http://127.0.0.1:{server.server_port}/#token={bridge.token}", flush=True)

    try:

        await asyncio.Event().wait()

    finally:

        application.mcp_stop.set()
        await application.integrations.stop()

        await application.cancel()

        server.shutdown()

        server.server_close()

        application.journal.close()

