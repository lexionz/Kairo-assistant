import asyncio
import json
import pytest
from kairo.capabilities import Capabilities
from kairo.contracts import Events
from kairo.web import Bridge
from kairo.application import Application
from kairo.runtime import Runtime, SYSTEM
from test_core import setup


def test_public_research_does_not_prompt_but_edits_still_do(tmp_path):
    _, _, events, _, journal, _, tools = setup(tmp_path, False)
    reviews = []
    events.subscribe(lambda e: reviews.append(e) if e.kind == 'approval' else None)
    result = asyncio.run(tools.call('t', 'research_document', {'url': 'https://example.org/docs'}, set()))
    assert result['text'] and not reviews
    assert tools.items['project_edit'].approval and tools.items['project_run'].approval
    journal.close()


def test_adapter_lifecycle_approval_persistence_and_live_dispatch(tmp_path):
    _, _, _, _, journal, research, tools = setup(tmp_path)
    registry = Capabilities(tools, research, journal.directory)
    registry.register()
    args = {'name': 'adapter_docs', 'url': 'https://example.org/docs', 'description': 'Read official docs'}
    async def run():
        assert not (await tools.call('t', 'capability_propose', args, set())).get('error')
        assert 'error' in await tools.call('t', 'capability_activate', {'name': args['name']}, set())
        assert (await tools.call('t', 'capability_test', {'name': args['name']}, set()))['passed']
        assert (await tools.call('t', 'capability_activate', {'name': args['name']}, set()))['registered'] == args['name']
        assert (await tools.call('t', 'capability_read', {'name': args['name']}, set()))['text']
        assert tools.items[args['name']].schema()['function']['parameters']['properties'] == {}
    asyncio.run(run())
    restarted = Capabilities(tools, research, journal.directory)
    assert restarted.records[args['name']]['status'] == 'proposed'
    with pytest.raises(ValueError):
        asyncio.run(restarted.read({'name': args['name']}))
    journal.close()


@pytest.mark.parametrize('url', ['http://example.org', 'https://u:p@example.org', 'https://example.org?key=abc', 'https://example.org/#token', 'file:///C:/file', 'https://example.org:8443'])
def test_adapter_refuses_credentials_and_dynamic_endpoints(url):
    with pytest.raises(ValueError):
        Capabilities.validate({'name': 'adapter_docs', 'url': url, 'description': 'Docs'})


def test_adapter_denial_never_registers(tmp_path):
    _, _, _, _, journal, research, tools = setup(tmp_path, False)
    registry = Capabilities(tools, research, journal.directory)
    registry.register()
    registry.propose({'name': 'adapter_docs', 'url': 'https://example.org/docs', 'description': 'Docs'})
    async def run():
        await registry.test({'name': 'adapter_docs'})
        denied = set()
        result = await tools.call('t', 'capability_activate', {'name': 'adapter_docs'}, denied)
        assert 'denied' in result['error'].lower()
        assert 'adapter_docs' not in tools.items
    asyncio.run(run())
    journal.close()


def test_bridge_keeps_presence_audio_and_review_across_events(tmp_path):
    app = Application(tmp_path)
    bridge = Bridge(app, None)
    app.events.emit('presence', mode='active')
    app.events.emit('audio', level=42)
    app.events.emit('approval', token='test', task='task', tool='project_edit')
    app.events.emit('notice', text='Unrelated event')
    snapshot = bridge.read(bridge.sequence)
    assert snapshot['presence'] == 'active' and snapshot['audio'] == 42
    assert snapshot['approval']['token'] == 'test'
    app.events.emit('approval_closed')
    assert bridge.read(0)['approval'] is None
    assert bridge.read(0)['presence'] == 'active'
    app.journal.close()


def test_repair_limit_stops_repeated_execution(tmp_path):
    _, workspace, events, _, journal, research, tools = setup(tmp_path)
    class Brain:
        count = 0
        async def complete(self, messages, schemas):
            self.count += 1
            if self.count == 5:
                assert 'Repair limit' in messages[-1]['content']
                return {'content': 'Blocked: the action failed.'}
            return {'tool_calls': [{'id': str(self.count), 'type': 'function', 'function': {'name': 'project_read', 'arguments': json.dumps({'project': 'AURORA', 'path': 'absent.py'})}}]}
    observed = []
    events.subscribe(lambda e: observed.append(e))
    asyncio.run(Runtime(Brain(), tools, workspace, research, journal, events).run('Inspect missing source'))
    assert len([e for e in observed if e.kind == 'workflow' and e.payload['stage'] == 'repair']) == 3
    assert any(e.kind == 'workflow' and e.payload['stage'] == 'verify' for e in observed)
    assert 'Do not invent a creator' in SYSTEM and 'may currently be Gemini' in SYSTEM
    journal.close()


def test_explicit_wake_consent_is_restored_without_implicit_enable(tmp_path):
    from kairo.wake import Presence
    app = Application(tmp_path)
    presence = Presence(app)
    calls = []
    async def enable(claps, threshold): calls.append((claps, threshold))
    presence.enable = enable
    asyncio.run(presence.restore_consent())
    assert not calls
    presence.claps = True
    presence.remember_consent(True)
    asyncio.run(presence.restore_consent())
    assert calls == [(True, .35)]
    presence.remember_consent(False)
    asyncio.run(presence.restore_consent())
    assert len(calls) == 1
    app.journal.close()
