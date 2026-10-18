import asyncio
import math
import struct
import time


def output_device(sd, config):
    selector = config.get("output_selector")
    if selector:
        matches = [i for i, d in enumerate(sd.query_devices()) if d["max_output_channels"] and d["name"] == selector["name"] and sd.query_hostapis(d["hostapi"])["name"] == selector["hostapi"]]
        if len(matches) != 1:
            raise ValueError("Configured output is unavailable; select an output in Settings")
        return matches[0]
    legacy = config.get("output_device")
    if isinstance(legacy, str):
        matches = [d for d in sd.query_devices() if legacy.casefold() in d["name"].casefold()]
        if matches and all(d["max_output_channels"] == 0 for d in matches):
            return None  # Migrate an input-only device mistakenly saved as the speaker.
    return legacy


def pcm_level(data):
    count = len(data) // 2
    if not count:
        return 0
    samples = struct.unpack('<' + 'h' * count, data[:count * 2])
    return min(100, math.sqrt(sum(x * x for x in samples) / count) / 40)


class LiveAudio:
    def __init__(self, events, config):
        self.events, self.config = events, config
        self.input = None
        self.output = None
        self.capture = asyncio.Queue(maxsize=200)
        self.playback = asyncio.Queue(maxsize=400)
        self.released = asyncio.Event()
        self.player = None
        self.tail_until = 0
        self.on_error = None
        self.continuous = False

    async def microphone(self):
        import sounddevice as sd
        await asyncio.sleep(max(0, self.tail_until - time.monotonic()))
        self.released.clear()
        while not self.capture.empty():
            self.capture.get_nowait()
        loop = asyncio.get_running_loop()

        def enqueue(data):
            if self.released.is_set():
                return
            if self.capture.full():
                self.events.emit("notice", text="Microphone queue overflow; capture stopped")
                self.release()
                return
            self.capture.put_nowait(data)

        def callback(data, frames, timing, status):
            loop.call_soon_threadsafe(enqueue, bytes(data))

        self.input = sd.RawInputStream(samplerate=16000, blocksize=1024, channels=1, dtype="int16", device=self.config.get("input_device"), callback=callback)
        try:
            self.input.start()
            self.events.emit("state", state="listening", text="Gemini Live · microphone on")
            while not self.released.is_set() or not self.capture.empty():
                try:
                    data = await asyncio.wait_for(self.capture.get(), .1)
                except TimeoutError:
                    continue
                self.events.emit("audio", level=pcm_level(data))
                yield data
        finally:
            self.input.abort()
            self.input.close()
            self.input = None
            self.events.emit("microphone", active=False)

    def release(self):
        self.released.set()

    async def queue(self, data):
        if len(data) % 2:
            raise ValueError("Invalid PCM16 output frame")
        if self.player and self.player.done():
            self.player.result()
        if not self.player:
            self.player = asyncio.create_task(self._play())
            self.player.add_done_callback(self._player_finished)
        for offset in range(0, len(data), 2400):
            await asyncio.wait_for(self.playback.put(data[offset:offset + 2400]), 15)

    def _player_finished(self, task):
        if not task.cancelled() and task.exception() and self.on_error:
            self.on_error(task.exception())

    async def _play(self):
        import sounddevice as sd
        device = output_device(sd, self.config)
        if device is None and self.config.get("output_device"):
            self.events.emit("notice", text="Saved output is an input-only microphone; using Windows default speakers. Choose an output in Settings to save it.")
        info = sd.query_devices(device, "output")
        sd.check_output_settings(device=device, samplerate=24000, channels=1, dtype="int16")
        self.events.emit("notice", text="Voice output: " + info["name"] + " · 24 kHz PCM16")
        self.output = sd.RawOutputStream(samplerate=24000, blocksize=1024, channels=1, dtype="int16", device=device)
        try:
            self.output.start()
            while True:
                data = await self.playback.get()
                try:
                    self.events.emit("state", state="speaking", text="Gemini Live · responding")
                    writing = asyncio.create_task(asyncio.to_thread(self.output.write, data))
                    try:
                        await asyncio.shield(writing)
                    except asyncio.CancelledError:
                        self.output.abort()
                        await asyncio.gather(writing, return_exceptions=True)
                        raise
                    self.events.emit("audio", level=pcm_level(data))
                    self.tail_until = time.monotonic() + float(self.output.latency) + .25
                finally:
                    self.playback.task_done()
                if self.continuous and self.playback.empty():
                    self.events.emit("state", state="listening", text="Conversation active · microphone on")
        finally:
            if self.output:
                self.output.abort()
                self.output.close()
                self.output = None

    async def drain(self):
        joining = asyncio.create_task(self.playback.join())
        try:
            if self.player:
                done, _ = await asyncio.wait([joining, self.player], timeout=90, return_when=asyncio.FIRST_COMPLETED)
                if self.player in done:
                    self.player.result()
                if not done:
                    raise TimeoutError("Audio playback timed out")
            await joining
            await asyncio.sleep(max(0, self.tail_until - time.monotonic()))
        finally:
            joining.cancel()

    async def stop(self):
        self.release()
        await self.interrupt()

    async def interrupt(self):
        if self.output:
            self.output.abort()
        if self.player:
            self.player.cancel()
            await asyncio.gather(self.player, return_exceptions=True)
            self.player = None
        while not self.playback.empty():
            self.playback.get_nowait()
            self.playback.task_done()
