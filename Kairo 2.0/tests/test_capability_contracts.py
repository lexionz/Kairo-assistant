"""Safety contracts runnable with the standard library when pytest is unavailable."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from kairo.application import Application
from kairo.capabilities import Capabilities
from kairo.contracts import Tool, parameters
from kairo.gemini_live import GeminiLive
from kairo.web import Bridge
from kairo.wake import Presence


class CapabilityContracts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.app = Application(Path(self.temporary.name))
        self.app.research.fetcher = lambda url: (url, 'Public documentation', {})
        self.reviews = []
        self.allow = True
        def review(event):
            if event.kind == 'approval':
                self.reviews.append(event.payload['tool'])
                self.app.authority.decide(event.payload['token'], event.payload['task'], self.allow)
        self.app.events.subscribe(review)

    def tearDown(self):
        self.app.journal.close()
        self.temporary.cleanup()

    async def call(self, name, args):
        return await self.app.tools.call('test', name, args, set())

    async def prepare_adapter(self):
        args = {'name': 'adapter_docs', 'url': 'https://example.org/docs', 'description': 'Public docs'}
        self.app.capabilities.propose(args)
        await self.app.capabilities.test({'name': 'adapter_docs'})

    async def test_read_works_without_prompt(self):
        result = await self.call('research_document', {'url': 'https://example.org/docs'})
        self.assertEqual(result['text'], 'Public documentation')
        self.assertEqual(self.reviews, [])

    async def test_untested_adapter_cannot_activate(self):
        self.app.capabilities.propose({'name': 'adapter_docs', 'url': 'https://example.org/docs', 'description': 'Docs'})
        result = await self.call('capability_activate', {'name': 'adapter_docs'})
        self.assertIn('Test this adapter', result['error'])
        self.assertNotIn('adapter_docs', self.app.tools.items)

    async def test_activation_denial_is_sticky(self):
        await self.prepare_adapter()
        self.allow = False
        result = await self.call('capability_activate', {'name': 'adapter_docs'})
        self.assertIn('denied', result['error'].lower())
        self.allow = True
        result = await self.call('capability_activate', {'name': 'adapter_docs'})
        self.assertIn('Denied', result['error'])
        self.assertNotIn('adapter_docs', self.app.tools.items)

    async def test_live_dispatch_and_restart_do_not_bypass_activation(self):
        await self.prepare_adapter()
        result = await self.call('capability_activate', {'name': 'adapter_docs'})
        self.assertEqual(result['registered'], 'adapter_docs')
        self.assertEqual((await self.call('capability_read', {'name': 'adapter_docs'}))['text'], 'Public documentation')
        restarted = Capabilities(self.app.tools, self.app.research, self.app.directory)
        self.assertEqual(restarted.records['adapter_docs']['status'], 'proposed')
        with self.assertRaises(ValueError):
            await restarted.read({'name': 'adapter_docs'})

    async def test_changed_adapter_invalidates_review(self):
        await self.prepare_adapter()
        prepared = self.app.capabilities.prepare_activation({'name': 'adapter_docs'})
        self.app.capabilities.propose({'name': 'adapter_docs', 'url': 'https://example.org/changed', 'description': 'Changed'})
        with self.assertRaises(ValueError):
            self.app.capabilities.activate(prepared)

    async def test_cancellation_during_approval_never_activates(self):
        await self.prepare_adapter()
        self.app.events.listeners.clear()
        pending = asyncio.create_task(self.call('capability_activate', {'name': 'adapter_docs'}))
        await asyncio.sleep(0)
        self.assertIsNotNone(self.app.authority.pending)
        pending.cancel()
        with self.assertRaises(asyncio.CancelledError): await pending
        self.assertIsNone(self.app.authority.pending)
        self.assertNotIn('adapter_docs', self.app.tools.items)

    async def test_bridge_retains_review_and_presence(self):
        bridge = Bridge(self.app, asyncio.get_running_loop())
        self.app.events.emit('presence', mode='active')
        self.app.events.emit('audio', level=42)
        self.app.events.emit('approval', token='test-token', task='test', tool='adapter')
        self.app.events.emit('notice', text='A notice')
        snapshot = bridge.read(bridge.sequence)
        self.assertEqual(snapshot['presence'], 'active')
        self.assertEqual(snapshot['audio'], 42)
        self.assertEqual(snapshot['approval']['token'], 'test-token')

    async def test_wake_is_opt_in_and_remembered(self):
        presence = Presence(self.app)
        calls = []
        async def enable(claps, threshold): calls.append((claps, threshold))
        presence.enable = enable
        await presence.restore_consent()
        self.assertEqual(calls, [])
        presence.remember_consent(True)
        await presence.restore_consent()
        self.assertEqual(calls, [(False, .35)])
        presence.remember_consent(False)
        await presence.restore_consent()
        self.assertEqual(len(calls), 1)

    async def test_live_repair_limit_prevents_fourth_execution(self):
        from google.genai import types
        count = []
        self.app.tools.add(Tool('failing_tool', 'Test failure', parameters(), lambda a: a, lambda a: count.append(1) or {'error': 'test failure'}))
        live = self.app.live
        live.task = 'test'
        for number in range(4):
            await live.execute(types.FunctionCall(id=str(number), name='failing_tool', args={}))
        self.assertEqual(len(count), 3)
        self.assertIn('Repair limit', live.call_results['3']['error'])

    async def test_runtime_repair_limit_and_identity(self):
        from kairo.runtime import Runtime
        calls = []
        self.app.tools.add(Tool('failing_tool', 'Test failure', parameters(), lambda a: a, lambda a: calls.append(1) or {'error': 'test failure'}))
        class Brain:
            count = 0
            async def complete(brain, messages, tools):
                brain.count += 1
                if brain.count == 5:
                    return {'content': 'Blocked; no success claimed.'}
                return {'tool_calls': [{'id': str(brain.count), 'type': 'function', 'function': {'name': 'failing_tool', 'arguments': '{}'}}]}
        report = await Runtime(Brain(), self.app.tools, self.app.workspace, self.app.research, self.app.journal, self.app.events).run('Test repair limits')
        self.assertEqual(len(calls), 3)
        self.assertIn('Blocked', report['answer'])


if __name__ == '__main__': unittest.main()
