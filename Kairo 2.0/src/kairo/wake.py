import asyncio

import json

import os

import time

from pathlib import Path

from kairo.presence import WakePolicy, ClapDetector





class Presence:

    def __init__(self, app, show=lambda: None, hide=lambda: None):

        self.app, self.show, self.hide = app, show, hide

        self.policy = WakePolicy()

        self.worker = self.active = self.process = None

        self.claps = False

        self.threshold = .35

        self.lock = asyncio.Lock()

        app.events.subscribe(self.event)



    def event(self, event):

        if event.kind in {"approval", "panel"}:

            self.show()



    def remember_consent(self, enabled):
        path = self.app.directory / "wake-consent.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"enabled": enabled, "claps": self.claps, "threshold": self.threshold}), encoding="utf-8")
        temporary.replace(path)

    async def restore_consent(self):
        path = self.app.directory / "wake-consent.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("enabled") is True and type(data.get("claps")) is bool:
                await self.enable(data["claps"], float(data.get("threshold", .35)))
        except (ValueError, TypeError, OSError):
            self.app.events.emit("notice", text="Saved wake preference unavailable; enable listening in Settings")

    def status(self):

        self.app.events.emit("presence", mode=self.policy.state, claps=self.claps)



    async def enable(self, claps=False, threshold=.35):

        if self.policy.state != "disabled":

            raise ValueError("Disable listening before recalibrating")

        if not self.app.live:

            raise ValueError("Select Gemini Live before enabling wake listening")

        ClapDetector(threshold)

        self.claps, self.threshold = claps, threshold

        self.policy.enable()

        self.status()

        self.worker = asyncio.create_task(self.watch())



    async def stop_watcher(self):

        if self.worker and self.worker is not asyncio.current_task():

            self.worker.cancel()

            await asyncio.gather(self.worker, return_exceptions=True)

        self.worker = None



    async def watch(self):

        tasks = []

        try:

            tasks = [asyncio.create_task(self.phrase())]

            if self.claps:

                tasks.append(asyncio.create_task(self.clap()))

            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in done:

                task.result()

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            self.policy.disable()

            self.status()

            self.show()

            self.app.events.emit("state", state="error", text="Wake listening stopped: " + str(exc)[:220])

        finally:

            for task in tasks:

                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)



    async def phrase(self):

        exe = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'

        process = await asyncio.create_subprocess_exec(str(exe), '-NoProfile', '-NonInteractive', '-File', str(Path(__file__).with_name('wake.ps1')), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, creationflags=0x08000000)

        errors = asyncio.create_task(process.stderr.read())

        try:

            while line := await process.stdout.readline():

                result = json.loads(line)

                if result.get('ready'):

                    self.app.events.emit('state', state='sleeping', text='Listening for Hey Kairo')

                    continue

                if self.policy.wake(result['text'], result['confidence']):

                    asyncio.create_task(self.awaken())

                    await asyncio.Event().wait()

            diagnostic = (await errors).decode('utf-8', errors='replace')

            if 'recognizer' in diagnostic.lower():

                raise RuntimeError('English (US) speech recognition is unavailable in Windows.')

            if 'audio' in diagnostic.lower() or 'device' in diagnostic.lower():

                raise RuntimeError('Windows could not open the default microphone. Check its connection and permissions.')

            raise RuntimeError('Windows speech listener exited. ' + ' '.join(diagnostic.split())[:160])

        finally:

            if process.returncode is None:

                process.kill()

            await process.wait()

            await errors



    async def clap(self):

        import numpy as np

        import sounddevice as sd

        detector = ClapDetector(self.threshold)

        queue = asyncio.Queue(maxsize=50)

        loop = asyncio.get_running_loop()

        def enqueue(data):

            if not queue.full():

                queue.put_nowait(data)

        def callback(data, frames, timing, status):

            loop.call_soon_threadsafe(enqueue, bytes(data))

        stream = sd.RawInputStream(samplerate=16000, blocksize=320, channels=1, dtype='int16', device=self.app.config['brain'].get('input_device'), callback=callback)

        try:

            stream.start()

            self.app.events.emit('notice', text='Clap calibration: keep quiet for three seconds. Wake uses two claps.')

            while True:

                samples = np.frombuffer(await queue.get(), dtype='<i2').astype(float) / 32768

                if detector.feed(float(np.max(np.abs(samples))), float(np.sqrt(np.mean(samples ** 2))), time.monotonic()):

                    if self.policy.wake(clap=True):

                        asyncio.create_task(self.awaken())

                        await asyncio.Event().wait()

        finally:

            stream.abort()

            stream.close()



    async def awaken(self):

        async with self.lock:

            await self.stop_watcher()

            if self.policy.state != 'active':

                return

            self.show()

            self.status()

            self.active = asyncio.create_task(self.converse())



    async def converse(self):

        self.app.turn = asyncio.current_task()

        self.app.live.on_sleep = lambda: asyncio.create_task(self.sleep())

        try:

            await self.app.live.conversation()

        except asyncio.CancelledError:

            raise

        except Exception:

            self.policy.disable()

            self.status()

            self.show()

            self.app.events.emit('state', state='error', text='Conversation disconnected. Listening disabled; no action replayed. Review activity, then enable listening again.')

        finally:

            self.app.turn = None



    async def sleep(self):

        async with self.lock:

            if self.policy.state == 'disabled':

                return

            await self.app.cancel()

            self.policy.sleep()

            self.status()

            self.hide()

            await self.stop_watcher()

            self.worker = asyncio.create_task(self.watch())



    async def disable(self):

        async with self.lock:

            self.policy.disable()

            await self.stop_watcher()

            await self.app.cancel()

            self.status()

            self.app.events.emit('state', state='idle', text='Listening disabled · microphone off')

