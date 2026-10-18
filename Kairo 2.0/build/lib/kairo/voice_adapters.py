import asyncio
import json
import os
from pathlib import Path


class VoicePipeline:
    def __init__(self, source, speaker):
        self.source, self.speaker = source, speaker

    async def listen(self):
        return await self.source.listen()

    def release(self):
        self.source.release()

    async def speak(self, text):
        await self.speaker.speak(text)

    async def stop(self):
        await self.source.stop()
        if self.speaker is not self.source:
            await self.speaker.stop()


class OmniVoiceSpeaker:
    def __init__(self, events, config):
        self.events, self.config = events, config
        self.process = None

    async def speak(self, text):
        executable = Path(self.config.get("python", ""))
        model = Path(self.config.get("model_path", ""))
        if not executable.is_absolute() or not executable.is_file() or not model.is_absolute() or not model.is_dir():
            raise ValueError("OmniVoice needs an installed Python environment and an absolute local model directory")
        self.events.emit("state", state="speaking", text="Rendering local voice · microphone off")
        environment = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "PATH", "TEMP", "TMP", "USERPROFILE", "WINDIR"}}
        environment["HF_HUB_OFFLINE"] = "1"
        environment["TRANSFORMERS_OFFLINE"] = "1"
        self.process = await asyncio.create_subprocess_exec(str(executable), str(Path(__file__).with_name("omnivoice_worker.py")),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            env=environment, **({"creationflags": 0x08000000} if os.name == "nt" else {}))
        try:
            request = {"model": str(model), "device": self.config.get("device", "cpu"), "text": text[:5000]}
            await asyncio.wait_for(self.process.communicate(json.dumps(request).encode()), 180)
            if self.process.returncode:
                raise RuntimeError("Local voice sidecar failed. Check its environment, model and audio output device; written response remains available.")
        finally:
            await self.stop()
            self.process = None

    async def stop(self):
        if self.process and self.process.returncode is None:
            try:
                self.process.kill()
            except ProcessLookupError:
                pass
            await self.process.wait()
