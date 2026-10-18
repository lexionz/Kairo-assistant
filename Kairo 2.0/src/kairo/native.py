"""Full-panel WebView2 shell; the private loopback URL never leaves the process UI."""
import asyncio
import ctypes
import os
import threading
from pathlib import Path
from kairo.web import Bridge, make_server
from kairo.wake import Presence


class NativeHost:
    def __init__(self, app, static):
        self.app, self.static = app, Path(static)
        self.loop = asyncio.new_event_loop()
        self.thread = self.server = self.server_thread = None

    def start_backend(self):
        if not (self.static / 'index.html').is_file():
            raise RuntimeError('Build the KAIRO UI first with Setup-KAIRO.cmd')
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.bridge = Bridge(self.app, self.loop)
        self.server = make_server(self.bridge, self.static)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        return f'http://127.0.0.1:{self.server.server_port}/#token={self.bridge.token}'

    async def cleanup(self):
        self.app.mcp_stop.set()
        await self.app.integrations.stop()
        self.app.companion.revoke()
        if self.app.companion_server:
            await asyncio.to_thread(self.app.companion_server.shutdown)
            self.app.companion_server.server_close()
        if getattr(self.app, 'presence', None):
            await self.app.presence.disable()
        else:
            await self.app.cancel()
        self.app.journal.close()

    def close(self):
        if self.thread:
            asyncio.run_coroutine_threadsafe(self.cleanup(), self.loop).result(timeout=20)
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server_thread.join(timeout=5)
        if self.thread:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=5)
            self.loop.close()
            self.thread = None

    def run(self, smoke=False):
        import webview
        webview.settings["ALLOW_DOWNLOADS"] = True
        if os.name == 'nt':
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('KAIRO.Desktop.Voice')
        url = self.start_backend()
        window = webview.create_window('KAIRO', url, width=1280, height=850, min_size=(800, 600))
        host = self
        class IndicatorAPI:
            def stop_sharing(self):
                host.loop.call_soon_threadsafe(host.app.companion.stop_mirroring)
            def disable(self):
                host.app.presence.remember_consent(False)
                asyncio.run_coroutine_threadsafe(host.app.presence.disable(), host.loop)
            def show(self):
                window.show()
                window.restore()
        indicator = webview.create_window('KAIRO · listening', html='<html><body style="background:#02050a;color:#a6d9ff;font:15px Segoe UI;padding:10px"><p>Local wake listening is on</p><button onclick="pywebview.api.disable()">Disable listening</button> <button onclick="pywebview.api.show()">Open KAIRO</button></body></html>', js_api=IndicatorAPI(), width=340, height=150, hidden=True, on_top=True, resizable=False)
        sharing = webview.create_window('KAIRO · screen sharing', html='<html><body style="background:#02050a;color:#a6d9ff;font:15px Segoe UI;padding:10px"><p>Your screen is being shared</p><button onclick="pywebview.api.stop_sharing()">Stop sharing</button></body></html>', js_api=IndicatorAPI(), width=330, height=140, hidden=True, on_top=True, resizable=False)
        quitting = threading.Event()
        def show():
            window.show()
            window.restore()
            indicator.hide()
        def hide():
            indicator.show()
            window.minimize()
        self.app.presence = Presence(self.app, show, hide)
        def event(event):
            if event.kind == 'companion_share':
                sharing.show() if event.payload['active'] else sharing.hide()
            if event.kind == 'presence' and event.payload['mode'] == 'disabled':
                indicator.hide()
            if event.kind == 'presence':
                title = {'disabled': 'microphone off', 'sleeping': 'local wake listening', 'active': 'microphone on'}[event.payload['mode']]
                window.set_title('KAIRO · ' + title)
        self.app.events.subscribe(event)
        def indicator_closing():
            if quitting.is_set():
                return True
            self.app.presence.remember_consent(False)
            asyncio.run_coroutine_threadsafe(self.app.presence.disable(), self.loop)
            indicator.hide()
            return False
        indicator.events.closing += indicator_closing
        def sharing_closing():
            if quitting.is_set():
                return True
            self.loop.call_soon_threadsafe(self.app.companion.stop_mirroring)
            sharing.hide()
            return False
        sharing.events.closing += sharing_closing
        def closed():
            quitting.set()
            indicator.destroy()
            sharing.destroy()
        window.events.closed += closed
        def startup():
            window.events.loaded.wait(20)
            asyncio.run_coroutine_threadsafe(self.app.presence.restore_consent(), self.loop)
        def smoke_check():
            window.events.loaded.wait(20)
            import time
            time.sleep(2)
            result = window.evaluate_js('({title:document.title, panelHeight:document.querySelector(".assistant-panel")?.getBoundingClientRect().height, buttons:Array.from(document.querySelectorAll("button")).map(b=>b.textContent), text:document.body.innerText})')
            if smoke:
                print(__import__('json').dumps(result), flush=True)
                window.destroy()
        try:
            webview.start(smoke_check if smoke else startup, gui='edgechromium', private_mode=True)
        finally:
            self.close()
