import asyncio
import json
import os
from pathlib import Path
from kairo.authority import Authority
from kairo.contracts import Events, Tool, parameters
from kairo.inference import CompatibleBrain
from kairo.journal import Journal
from kairo.research import Research
from kairo.runtime import Runtime
from kairo.tools import Tools, register
from kairo.voice import WindowsVoice
from kairo.workspace import Workspace


class Application:
    def __init__(self, directory=None, brain=None, voice=None):
        self.directory = Path(directory or os.environ.get("KAIRO_DATA_DIR") or Path(os.environ.get("APPDATA", str(Path.home()))) / "KAIRO")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.config_file = self.directory / "config.json"
        if not self.config_file.exists():
            self.config_file.write_text(Path(__file__).with_name("default.json").read_text(), encoding="utf-8")
        self.config = json.loads(self.config_file.read_text(encoding="utf-8"))
        self.events = Events()
        self.journal = Journal(self.directory)
        self.authority = Authority(self.events)
        from kairo.companion import Companion, WindowsControls
        self.companion = Companion(self.authority, self.journal, WindowsControls())
        self.companion_server = None
        self.workspace = Workspace(self.config.get("projects", {}), self.directory)
        self.research = Research(max_sources=self.config.get("research", {}).get("max_sources", 12))
        self.tools = Tools(self.authority, self.journal, self.events)
        register(self.tools, self.workspace, self.research, self.journal)
        from kairo.capabilities import Capabilities
        self.capabilities = Capabilities(self.tools, self.research, self.directory)
        self.capabilities.register()
        from kairo.integrations import Integrations
        self.integrations = Integrations(self)
        self.integrations.register()
        self.tools.add(Tool("interface_settings", "Open KAIRO settings when the user asks; does not change settings", parameters(), lambda a: a, lambda a: self.open_settings()))
        self.runtime = Runtime(brain or CompatibleBrain(self.config["brain"]), self.tools, self.workspace, self.research, self.journal, self.events)
        from kairo.specialist import ResearchSpecialist
        self.specialist = ResearchSpecialist(self.runtime.brain, self.tools, self.research)
        self.tools.add(Tool("research_deep", "Delegate a bounded research question to a read-only specialist. Shared bounded public-web source budget.", parameters(question=2000), lambda a: a, lambda a: self.specialist.run(self.runtime.task_id, a["question"])))
        from kairo.voice_adapters import VoicePipeline, OmniVoiceSpeaker
        windows_voice = WindowsVoice(self.events)
        output_config = self.config.get("voice", {})
        speaker = OmniVoiceSpeaker(self.events, output_config) if output_config.get("output") == "omnivoice" else windows_voice
        self.voice = voice or VoicePipeline(windows_voice, speaker)
        self.turn = None
        self.mcp_stop = asyncio.Event()
        self.mcp_running = False
        self.live = None
        if brain is None and self.config["brain"].get("provider") == "gemini_live":
            from kairo.gemini_live import GeminiLive
            self.tools.items.pop("research_deep", None)
            self.live = GeminiLive(self.config["brain"], self.tools, self.workspace, self.journal, self.research, self.events)

    def open_settings(self):
        self.events.emit("panel", panel="settings")
        return {"opened": "settings"}

    async def request(self, text=None):
        if self.turn:
            return
        self.turn = asyncio.current_task()
        try:
            if self.live:
                await self.live.run(text)
                self.events.emit("state", state="success", text="Gemini Live turn finished · microphone off")
                return
            if text is None:
                text = await self.voice.listen()
            if not text.strip():
                raise ValueError("No speech detected; check the Windows default microphone")
            self.events.emit("transcript", text=text)
            report = await self.runtime.run(text)
            await self.voice.speak(report["answer"])
            self.events.emit("state", state="success", text="Finished · microphone off")
        except asyncio.CancelledError:
            self.events.emit("state", state="interrupted", text="Stopped · microphone off")
        except Exception as exc:
            self.events.emit("state", state="error", text=str(exc)[:250])
        finally:
            await self.voice.stop()
            self.turn = None

    async def cancel(self):
        self.runtime.cancel()
        self.authority.cancel()
        turn = self.turn
        if turn and turn is not asyncio.current_task():
            turn.cancel()
            await asyncio.gather(turn, return_exceptions=True)
        if self.live:
            await self.live.stop()
        await self.voice.stop()

    def release(self):
        if self.live:
            self.live.release()
        else:
            self.voice.release()

    async def connect_mcp(self):
        return await self.integrations.connect(self.config["mcp"])

    async def snapshot(self):
        self.events.emit("snapshot", memories=self.journal.memories(), knowledge=self.journal.knowledge(), activity=self.journal.activity())

    async def save_settings(self, endpoint, model, provider="compatible", voice="Charon"):
        if getattr(self, "presence", None) and self.presence.policy.state != "disabled":
            raise ValueError("Disable wake listening before changing provider settings")
        if self.turn:
            self.events.emit("notice", text="Stop the current task before changing settings")
            return
        if self.live:
            await self.live.stop()
            self.live = None
        self.config["brain"] = {**self.config["brain"], "provider": provider, "endpoint": endpoint.strip(), "model": model.strip(), "voice": voice}
        temporary = self.config_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        temporary.replace(self.config_file)
        self.runtime.brain = CompatibleBrain(self.config["brain"])
        self.specialist.brain = self.runtime.brain
        if provider == "gemini_live":
            from kairo.gemini_live import GeminiLive
            self.tools.items.pop("research_deep", None)
            self.live = GeminiLive(self.config["brain"], self.tools, self.workspace, self.journal, self.research, self.events)
        elif "research_deep" not in self.tools.items:
            self.tools.add(Tool("research_deep", "Bounded read-only research specialist", parameters(question=2000), lambda a: a, lambda a: self.specialist.run(self.runtime.task_id, a["question"])))
        self.events.emit("notice", text="Provider saved. Context will be sent to this endpoint when you submit a task.")
