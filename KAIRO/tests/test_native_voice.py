import asyncio
from types import SimpleNamespace
import pytest
from kairo.presence import WakePolicy, ClapDetector, sleep_command
from kairo.companion import Companion, lan_address, WindowsControls
from kairo.native import NativeHost
from kairo.application import Application
from test_gemini_live import setup, Factory


def test_wake_opt_in_confidence_cooldown_and_sleep():
    now = [0]
    policy = WakePolicy(lambda: now[0])
    assert not policy.wake('hey kairo', 1)
    policy.enable()
    assert not policy.wake('hey car', 1)
    assert not policy.wake('hey kairo', .7)
    assert policy.wake('Hey Kairo', .9)
    assert not policy.wake(clap=True)
    policy.sleep()
    assert not policy.wake(clap=True)
    now[0] += 6
    assert policy.wake(clap=True)
    policy.disable()
    assert not policy.wake(clap=True)


@pytest.mark.parametrize('text', ['Kairo, go to sleep.', 'go to sleep', 'Kairo sleep'])
def test_sleep_phrases(text):
    assert sleep_command(text)


@pytest.mark.parametrize('text', ['do not go to sleep', 'explain go to sleep', 'Kairo go to sleep tomorrow'])
def test_sleep_false_positives(text):
    assert not sleep_command(text)


def test_clap_calibration_double_impulse_and_sustained_noise_rejection():
    detector = ClapDetector()
    for i in range(150):
        assert not detector.feed(.01, .005, i * .02)
    for i in range(4):
        assert not detector.feed(.01, .005, 3 + i * .02)
    assert not detector.feed(.9, .1, 3.1)
    for i in range(4):
        assert not detector.feed(.01, .005, 3.2 + i * .02)
    assert detector.feed(.9, .1, 3.5)
    for i in range(200):
        assert not detector.feed(.9, .5, 4 + i * .02)


def test_continuous_two_turns_do_not_release_microphone(tmp_path, monkeypatch):
    async def run():
        factory = Factory('wait')
        app, live, audio = setup(tmp_path, monkeypatch, factory)
        live.input_text = 'Kairo, go to sleep.'  # A prior sleeping session must not poison the next wake.
        async def microphone():
            yield b'\0\0' * 10
            await asyncio.Event().wait()
        audio.microphone = microphone
        task = asyncio.create_task(live.conversation())
        while not factory.sessions:
            await asyncio.sleep(.001)
        await factory.sessions[0].finish()
        await asyncio.sleep(.02)
        await factory.sessions[0].finish()
        await asyncio.sleep(.02)
        assert not task.done()
        assert not audio.released
        assert len(audio.chunks) == 2
        assert len(factory.sessions) == 1
        assert live.input_text == ''
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert live.task is None and live.session is None
        app.journal.close()
    asyncio.run(run())


def test_continuous_sleep_callback(tmp_path, monkeypatch):
    from google.genai import types
    async def run():
        factory = Factory('wait')
        app, live, audio = setup(tmp_path, monkeypatch, factory)
        called = asyncio.Event()
        live.on_sleep = called.set
        async def microphone():
            yield b'\0\0'
            await asyncio.Event().wait()
        audio.microphone = microphone
        task = asyncio.create_task(live.conversation())
        while not factory.sessions:
            await asyncio.sleep(.001)
        await factory.sessions[0].messages.put(types.LiveServerMessage(server_content=types.LiveServerContent(input_transcription=types.Transcription(text='Kairo, go to sleep.'))))
        await asyncio.wait_for(called.wait(), 1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        app.journal.close()
    asyncio.run(run())


def test_native_backend_shutdown_releases_port(tmp_path):
    import socket
    static = tmp_path/'ui'
    static.mkdir()
    (static/'index.html').write_text('KAIRO')
    host = NativeHost(Application(tmp_path/'state'), static)
    url = host.start_backend()
    port = host.server.server_port
    assert url.startswith('http://127.0.0.1:')
    host.close()
    with socket.socket() as sock:
        assert sock.connect_ex(('127.0.0.1', port)) != 0


def companion():
    now = [0]
    class Authority:
        async def request(self, *args):
            return True
    journal = SimpleNamespace(record=lambda *args: None)
    return Companion(Authority(), journal, clock=lambda: now[0]), now


def test_pairing_expiry_scope_revocation_and_one_use():
    c, now = companion()
    code = c.issue(['pointer'])['code']
    token = c.pair(code)['token']
    with pytest.raises(PermissionError):
        c.pair(code)
    c.authenticate(token, 'pointer')
    with pytest.raises(PermissionError):
        c.authenticate(token, 'screen')
    c.revoke()
    with pytest.raises(PermissionError):
        c.authenticate(token, 'pointer')
    code = c.issue(['screen'])['code']
    now[0] = 121
    with pytest.raises(PermissionError):
        c.pair(code)


def test_pairing_attempt_limit():
    c, _ = companion()
    code = c.issue(['pointer'])['code']
    for _ in range(5):
        with pytest.raises(PermissionError):
            c.pair('wrong')
    with pytest.raises(PermissionError):
        c.pair(code)


@pytest.mark.parametrize('address', ['0.0.0.0', '127.0.0.1', '8.8.8.8', '::', '169.254.1.1'])
def test_lan_binding_rejects_non_private_interfaces(address):
    with pytest.raises(ValueError):
        lan_address(address)


def test_companion_replay_and_revoke_during_confirmation():
    async def run():
        c, now = companion()
        actions = []
        c.adapter = SimpleNamespace(prepare=lambda action, args: args, execute=lambda action, args: actions.append(action) or {})
        token = c.pair(c.issue(['pointer'])['code'])['token']
        await c.control(token, 1, 'move', {'dx': 1, 'dy': 0})
        with pytest.raises(PermissionError):
            await c.control(token, 1, 'move', {})
        async def revoke(*args):
            c.revoke()
            return True
        c.authority.request = revoke
        now[0] += 1
        with pytest.raises(PermissionError):
            await c.control(token, 2, 'click', {'button': 'left'})
        assert actions == ['move']
    asyncio.run(run())


def test_keyboard_cannot_send_enter_or_hotkeys():
    with pytest.raises(ValueError):
        WindowsControls().prepare('type', {'text': 'command\n'})
    with pytest.raises(ValueError):
        WindowsControls().prepare('window', {'command': 'anything'})
