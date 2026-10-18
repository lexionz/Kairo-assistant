import asyncio
import sys
from types import SimpleNamespace
import pytest
from kairo.live_audio import LiveAudio, output_device


def test_pcm24k_output_and_interrupt_preserves_capture(monkeypatch):
    written, settings = [], []
    class Stream:
        latency = 0
        def __init__(self, **kwargs):
            settings.append(kwargs)
        def start(self): pass
        def abort(self): pass
        def close(self): pass
        def write(self, data): written.append(data)
    sd = SimpleNamespace(RawOutputStream=Stream, query_devices=lambda *a: {'name':'Fixture speakers'}, check_output_settings=lambda **k: None)
    monkeypatch.setitem(sys.modules, 'sounddevice', sd)
    async def run():
        audio = LiveAudio(SimpleNamespace(emit=lambda *a, **k: None), {})
        pcm = b'\x01\x02' * 2400
        await audio.queue(pcm)
        await audio.drain()
        assert b''.join(written) == pcm
        assert settings[0]['samplerate'] == 24000
        assert settings[0]['channels'] == 1
        assert settings[0]['device'] is None
        await audio.interrupt()
        assert not audio.released.is_set()
        await audio.stop()
        assert audio.released.is_set()
    asyncio.run(run())


def test_missing_output_fails_explicitly():
    sd = SimpleNamespace(query_devices=lambda: [])
    with pytest.raises(ValueError, match='unavailable'):
        output_device(sd, {'output_selector': {'name':'Unplugged','hostapi':'MME'}})


def test_input_only_legacy_selection_uses_default_output():
    sd = SimpleNamespace(query_devices=lambda: [{'name': 'Microphone (Fixture)', 'max_output_channels': 0}])
    assert output_device(sd, {'output_device':'Fixture'}) is None


def test_output_failure_signals_conversation(monkeypatch):
    def fail(*a, **k): raise ValueError('No output')
    monkeypatch.setitem(sys.modules, 'sounddevice', SimpleNamespace(query_devices=fail))
    async def run():
        audio = LiveAudio(SimpleNamespace(emit=lambda *a, **k: None), {})
        failed = asyncio.Event()
        audio.on_error = lambda error: failed.set()
        await audio.queue(b'\0\0')
        await asyncio.wait_for(failed.wait(), 1)
        await audio.stop()
    asyncio.run(run())
