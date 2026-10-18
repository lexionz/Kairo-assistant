import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
import pytest
from google.genai import types
from kairo.application import Application
from kairo.contracts import Tool, parameters
from kairo.gemini_live import GeminiLive, DEFAULT_MODEL, build_config, api_key


class Audio:
    def __init__(self):
        self.chunks = []
        self.stopped = 0
        self.released = False

    def release(self):
        self.released = True

    async def queue(self, data):
        self.chunks.append(data)

    async def drain(self):
        pass

    async def stop(self):
        self.stopped += 1

    async def microphone(self):
        yield b'\0\0' * 1024


class Session:
    def __init__(self, mode):
        self.messages = asyncio.Queue()
        self.mode = mode
        self.sent = []
        self.responses = []
        self.input = []

    async def send_client_content(self, **kwargs):
        self.sent.append(kwargs)
        if self.mode == "tool":
            await self.messages.put(types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[types.FunctionCall(id="one", name="test_action", args={"text": "exact"})])))
        elif self.mode != "wait":
            await self.finish()

    async def finish(self):
        await self.messages.put(types.LiveServerMessage(session_resumption_update=types.LiveServerSessionResumptionUpdate(resumable=True, new_handle="test-handle")))
        await self.messages.put(types.LiveServerMessage(server_content=types.LiveServerContent(output_transcription=types.Transcription(text="Hello KAIRO"), model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b'\0\0' * 1024, mime_type="audio/pcm;rate=24000"))]))))
        await self.messages.put(types.LiveServerMessage(server_content=types.LiveServerContent(turn_complete=True)))

    async def send_realtime_input(self, **kwargs):
        self.input.append(kwargs)
        if kwargs.get("audio_stream_end"):
            await self.finish()

    async def send_tool_response(self, **kwargs):
        self.responses.append(kwargs)
        await self.finish()

    async def receive(self):
        while True:
            message = await self.messages.get()
            yield message
            if message.server_content and message.server_content.turn_complete:
                return

    async def close(self):
        pass


class Factory:
    def __init__(self, mode="normal", failures=()):
        self.mode = mode
        self.failures = list(failures)
        self.clients = []
        self.sessions = []
        self.configs = []

    def __call__(self, **kwargs):
        self.clients.append(kwargs)
        owner = self
        class Client:
            def __init__(self):
                self.aio = self
                self.live = self

            @asynccontextmanager
            async def connect(self, **config):
                owner.configs.append(config)
                if owner.failures:
                    raise ValueError(owner.failures.pop(0))
                session = Session(owner.mode)
                owner.sessions.append(session)
                yield session

            async def aclose(self):
                pass
        return Client()


def setup(tmp_path, monkeypatch, factory):
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-not-a-secret")
    app = Application(tmp_path)
    audio = Audio()
    live = GeminiLive(app.config["brain"], app.tools, app.workspace, app.journal, app.research, app.events, audio=audio, client_factory=factory)
    return app, live, audio


def test_active_configuration_and_optional_fallbacks(tmp_path, monkeypatch):
    app, live, audio = setup(tmp_path, monkeypatch, Factory())
    config = build_config({}, app.tools, []).model_dump(exclude_none=True)
    assert config["response_modalities"] == ["AUDIO"]
    assert config["speech_config"]["voice_config"]["prebuilt_voice_config"]["voice_name"] == "Charon"
    assert config["proactivity"] == {"proactive_audio": True}
    assert config["context_window_compression"] == {"sliding_window": {}}
    assert config["session_resumption"] == {}
    assert "input_audio_transcription" in config and "output_audio_transcription" in config
    assert "thinking_config" not in config and "realtime_input_config" not in config
    plain = build_config({}, app.tools, [], tuned=False, enhanced=False).model_dump(exclude_none=True)
    assert "media_resolution" not in plain and "proactivity" not in plain
    assert app.config["brain"]["model"] == DEFAULT_MODEL
    app.journal.close()


def test_live_text_audio_and_connection_reuse(tmp_path, monkeypatch):
    async def run():
        factory = Factory()
        app, live, audio = setup(tmp_path, monkeypatch, factory)
        try:
            first = await live.run("hello")
            assert first["answer"] == "Hello KAIRO"
            assert audio.chunks and live.handle == "test-handle"
            await live.run("again")
            assert len(factory.clients) == 1
            assert len(factory.sessions[0].sent) == 2
            await live.disconnect(keep_handle=True)
            await live.run(None)
            assert factory.configs[-1]["config"].session_resumption.handle == "test-handle"
            assert factory.sessions[-1].input[0]["audio"].mime_type == "audio/pcm;rate=16000"
            assert factory.sessions[-1].input[-1] == {"audio_stream_end": True}
        finally:
            await live.stop()
            assert live.handle is None
            app.journal.close()
    asyncio.run(run())


def test_live_tool_requires_ui_approval_and_deduplicates(tmp_path, monkeypatch):
    async def run():
        factory = Factory("tool")
        app, live, audio = setup(tmp_path, monkeypatch, factory)
        executions = []
        app.tools.add(Tool("test_action", "test", parameters(text=100), lambda a: a, lambda a: executions.append(a) or {"ok": True}, True))
        def approve(event):
            if event.kind == "approval":
                assert not executions
                app.authority.decide(event.payload["token"], event.payload["task"], True)
        app.events.subscribe(approve)
        try:
            await asyncio.wait_for(live.run("do action"), 2)
            assert executions == [{"text": "exact"}]
            await asyncio.wait_for(live.run("server replays identical ID"), 2)
            assert len(executions) == 1
            assert len(factory.sessions[0].responses) == 2
        finally:
            await live.stop()
            app.journal.close()
    asyncio.run(run())


def test_stop_cancels_approval_without_action(tmp_path, monkeypatch):
    async def run():
        app, live, audio = setup(tmp_path, monkeypatch, Factory("tool"))
        executions = []
        app.tools.add(Tool("test_action", "test", parameters(text=100), lambda a: a, lambda a: executions.append(a) or {}, True))
        turn = asyncio.create_task(live.run("pending"))
        for _ in range(100):
            if app.authority.pending:
                break
            await asyncio.sleep(.001)
        assert app.authority.pending
        turn.cancel()
        with pytest.raises(asyncio.CancelledError):
            await turn
        assert not executions and not app.authority.pending and audio.stopped
        assert live.handle is None
        app.journal.close()
    asyncio.run(run())


def test_compatibility_fallback_never_changes_model(tmp_path, monkeypatch):
    async def run():
        factory = Factory(failures=["INVALID_ARGUMENT media_resolution", "INVALID_ARGUMENT proactivity"])
        app, live, audio = setup(tmp_path, monkeypatch, factory)
        try:
            await live.run("hello")
            assert [c["http_options"]["api_version"] for c in factory.clients] == ["v1alpha", "v1alpha", "v1beta"]
            assert all(c["model"] == DEFAULT_MODEL for c in factory.configs)
        finally:
            await live.stop()
            app.journal.close()
    asyncio.run(run())


def test_key_is_required_and_not_in_default_configuration(tmp_path, monkeypatch):
    for name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "KAIRO_CREDENTIALS_FILE"]:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="locally"):
        api_key({})
