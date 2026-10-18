import asyncio
import json
import socket
from urllib.parse import urlsplit
import httpx
import pytest
from kairo.application import Application
from kairo.mcp_link import MCPLink, validate_config, check_request
from kairo.web import Bridge


@pytest.mark.parametrize('url',['https://example.com/mcp','http://localhost:8000/sse','http://user:pass@127.0.0.1/mcp','http://127.0.0.1/mcp?token=secret','file:///C:/mcp'])
def test_mcp_rejects_remote_and_credential_endpoints(url):
    with pytest.raises(ValueError): validate_config({'url':url,'allow':[]})


def test_mcp_transport_cannot_follow_announced_remote_endpoint():
    with pytest.raises(ValueError): asyncio.run(check_request(httpx.Request('POST','https://example.org/message')))


def test_actual_bundled_mcp_discovery_execution_and_revocation(tmp_path):
    async def run():
        app=Application(tmp_path)
        reviews=[]
        app.events.subscribe(lambda e:reviews.append(e) if e.kind=='approval' else None)
        try:
            status=await app.integrations.start_local()
            assert status['connected'] and len(status['tools'])==4
            port=urlsplit(status['config']['url']).port
            discovered=await app.integrations.discover(status['config'])
            assert {t['name'] for t in discovered['tools']}=={'get_current_time','get_system_info','word_count','format_json'}
            app.runtime.task_id='test'
            result=await app.integrations.call({'name':'mcp_word_count','arguments':json.dumps({'text':'KAIRO works locally'})})
            assert json.loads(result['content'][0]['text'])['words']==3
            assert not reviews
            await app.integrations.stop()
            assert not any(name.startswith('mcp_') for name in app.tools.items)
            with socket.socket() as s: assert s.connect_ex(('127.0.0.1',port))!=0
            with pytest.raises(ValueError): await app.integrations.call({'name':'mcp_word_count','arguments':'{}'})
        finally:
            await app.integrations.stop()
            app.journal.close()
    asyncio.run(run())


def test_custom_server_tools_are_not_trusted_from_annotations(tmp_path):
    async def run():
        host=Application(tmp_path/'host')
        guest=Application(tmp_path/'guest')
        try:
            status=await host.integrations.start_local()
            config={**status['config'],'allow':['get_current_time']}
            assert (await guest.integrations.connect(config))['connected']
            assert guest.tools.items['mcp_get_current_time'].approval
            guest.events.subscribe(lambda e:guest.authority.decide(e.payload['token'],e.payload['task'],False) if e.kind=='approval' else None)
            result=await guest.tools.call('t','mcp_get_current_time',{},set())
            assert 'denied' in result['error'].lower()
        finally:
            await guest.integrations.stop()
            await host.integrations.stop()
            guest.journal.close();host.journal.close()
    asyncio.run(run())


def test_plugin_preparation_never_activates_or_loads_code(tmp_path):
    app=Application(tmp_path)
    result=app.integrations.plugins.prepare({'plugin':'python_docs'})
    assert len(result['adapters'])==2
    assert all(a['status']=='proposed' for a in result['adapters'])
    assert all(a['name'] not in app.tools.items for a in result['adapters'])
    app.journal.close()


def test_ui_adapter_activation_binds_reviewed_url_and_hash(tmp_path):
    async def run():
        app=Application(tmp_path)
        app.research.fetcher=lambda url:(url,'Docs',{})
        app.capabilities.propose({'name':'adapter_test','url':'https://example.org/docs','description':'Docs'})
        await app.capabilities.test({'name':'adapter_test'})
        bridge=Bridge(app,asyncio.get_running_loop())
        with pytest.raises(ValueError,match='changed'):
            await bridge.command({'action':'adapter_activate','name':'adapter_test','url':'https://example.org/other'})
        prepared=app.capabilities.prepare_activation({'name':'adapter_test'})
        result=await bridge.command({'action':'adapter_activate',**{k:prepared[k] for k in ('name','url','sha256','tested_at')}})
        assert result['registered']=='adapter_test'
        app.journal.close()
    asyncio.run(run())
