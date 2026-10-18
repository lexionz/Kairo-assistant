import asyncio
import json
import os
from pathlib import Path


class WindowsVoice:
    def __init__(self, events):
        self.events = events
        self.process = None
        self.released = False

    async def _start(self, operation, extra=()):
        if os.name != "nt":
            raise RuntimeError("The default speech adapter requires Windows")
        if self.process:
            raise RuntimeError("Speech is already active")
        executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        self.process = await asyncio.create_subprocess_exec(str(executable), "-NoProfile", "-NonInteractive", "-File", str(Path(__file__).with_name("speech.ps1")), "-Operation", operation, *extra, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, creationflags=0x08000000)
        return self.process

    def release(self):
        self.released = True
        if self.process and self.process.stdin and not self.process.stdin.is_closing():
            self.process.stdin.write(b"finish\n")

    async def stop(self):
        if self.process and self.process.returncode is None:
            self.process.kill()
            await self.process.wait()

    async def listen(self):
        self.released = False
        self.events.emit("state", state="listening", text="Microphone on · release to finish")
        process = await self._start("listen")
        if self.released:
            self.release()
        text = ""
        try:
            async with asyncio.timeout(25):
                while line := await process.stdout.readline():
                    event = json.loads(line)
                    if "level" in event:
                        self.events.emit("audio", level=event["level"])
                    if "text" in event:
                        text = event["text"]
                await process.wait()
                if process.returncode:
                    raise RuntimeError("Windows dictation failed. Check the default microphone and installed speech language.")
            return text
        finally:
            await self.stop()
            self.process = None
            self.events.emit("microphone", active=False)

    async def speak(self, text):
        self.events.emit("state", state="speaking", text="Microphone off · responding")
        process = await self._start("speak")
        try:
            await asyncio.wait_for(process.communicate(text[:5000].encode("utf-8")), 90)
            if process.returncode:
                raise RuntimeError("Windows voice output failed; the written result is available in Activity")
        finally:
            await self.stop()
            self.process = None
