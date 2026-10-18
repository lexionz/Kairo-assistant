import asyncio
from google.genai import types
from test_gemini_live import Factory, setup


def test_barge_in_interrupts_playback_and_keeps_session(tmp_path, monkeypatch):
    async def run():
        factory = Factory('wait')
        app, live, audio = setup(tmp_path, monkeypatch, factory)
        interrupted = asyncio.Event()
        async def interrupt(): interrupted.set()
        audio.interrupt = interrupt
        async def microphone():
            yield b'\0\0'
            await asyncio.Event().wait()
        audio.microphone = microphone
        task = asyncio.create_task(live.conversation())
        while not factory.sessions: await asyncio.sleep(.001)
        await factory.sessions[0].messages.put(types.LiveServerMessage(server_content=types.LiveServerContent(interrupted=True)))
        await asyncio.wait_for(interrupted.wait(), 1)
        assert not task.done() and not audio.released
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        app.journal.close()
    asyncio.run(run())


def test_live_adapters_available_through_stable_declaration(tmp_path, monkeypatch):
    app, live, _ = setup(tmp_path, monkeypatch, Factory('wait'))
    app.research.fetcher = lambda url: (url, 'Official documentation', {})
    app.events.subscribe(lambda e: app.authority.decide(e.payload['token'], e.payload['task'], True) if e.kind == 'approval' else None)
    async def run():
        await live.connect()
        live.task = 'test-task'
        assert any(t['function']['name'] == 'capability_read' for t in app.tools.schemas())
        args = {'name': 'adapter_test', 'url': 'https://example.org/docs', 'description': 'Test docs'}
        app.capabilities.propose(args)
        await app.capabilities.test({'name': args['name']})
        await app.tools.call(live.task, 'capability_activate', {'name': args['name']}, set())
        await live.execute(types.FunctionCall(id='new-reader', name='capability_read', args={'name': args['name']}))
        assert live.call_results['new-reader']['text'] == 'Official documentation'
        await live.stop()
    asyncio.run(run())
    app.journal.close()
