"""Connection ownership and reviewed MCP setup for both provider paths."""
import asyncio
import json
import socket
from kairo.contracts import Tool, parameters
from kairo.mcp_link import MCPLink, validate_config
from kairo.plugins import PluginLibrary


class Integrations:
    def __init__(self, app):
        self.app = app
        self.link = None
        self.task = None
        self.stop_event = asyncio.Event()
        self.ready = asyncio.Event()
        self.error = None
        self.server = self.server_task = self.socket = None
        self.config = None
        self.plugins = PluginLibrary(app.capabilities)

    def status(self):
        return {'connected': bool(self.link and self.link.stack), 'connecting': bool(self.task and not self.ready.is_set()),
                'tools': list(self.link.names) if self.link else [], 'error': self.error,
                'local': self.server is not None, 'config': self.config}

    async def discover(self, config):
        # Discovery reads manifests only. Connection and invocation remain separate.
        async with asyncio.timeout(15):
            return await MCPLink().discover(validate_config(config))

    async def connect(self, config, trusted=()):
        if self.task and not self.task.done():
            raise ValueError('Disconnect the current integration first')
        self.config = validate_config(config)
        self.ready.clear()
        self.stop_event.clear()
        self.error = None
        async def own_connection():
            self.link = MCPLink()
            try:
                await self.link.connect(self.config, self.app.tools, trusted)
                self.app.events.emit('notice', text='Connected tools: ' + ', '.join(self.link.names))
                self.ready.set()
                await self.stop_event.wait()
            except asyncio.CancelledError:
                raise
            except Exception:
                self.error = 'Connection failed. Check that the local server is running and selected tools are supported.'
                self.app.events.emit('notice', text=self.error)
            finally:
                await self.link.close()
                self.ready.set()
        self.task = asyncio.create_task(own_connection())
        try:
            await asyncio.wait_for(self.ready.wait(), 15)
        except (asyncio.CancelledError, TimeoutError):
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            raise
        return self.status()

    async def start_local(self):
        if self.task and not self.task.done():
            raise ValueError('Disconnect the current integration first')
        from kairo.local_mcp import create_server, READ_ONLY_TOOLS
        import uvicorn
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        sock.listen(128)
        self.socket = sock
        port = sock.getsockname()[1]
        server = create_server(port)
        self.server = uvicorn.Server(uvicorn.Config(server.streamable_http_app(), host='127.0.0.1', port=port, log_level='warning', access_log=False))
        self.server_task = asyncio.create_task(self.server.serve(sockets=[sock]))
        try:
            async with asyncio.timeout(10):
                while not self.server.started:
                    if self.server_task.done():
                        self.server_task.result()
                        raise RuntimeError('Local MCP server did not start')
                    await asyncio.sleep(.02)
            result = await self.connect({'url': f'http://127.0.0.1:{port}/mcp', 'transport': 'streamable-http', 'allow': list(READ_ONLY_TOOLS)}, trusted=READ_ONLY_TOOLS)
            if not result['connected']:
                raise RuntimeError(result['error'])
            return result
        except BaseException:
            await self.stop()
            raise

    async def stop(self):
        self.stop_event.set()
        if self.task:
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None
        if self.server:
            self.server.should_exit = True
        if self.server_task:
            await asyncio.gather(self.server_task, return_exceptions=True)
        if self.socket:
            self.socket.close()
        self.server = self.server_task = self.socket = None
        return self.status()

    def prepare_connection(self, args):
        return validate_config({'url': args['url'], 'transport': args['transport'], 'allow': [x.strip() for x in args['tools'].split(',') if x.strip()]})

    async def call(self, args):
        if not args['name'].startswith('mcp_') or not self.link or args['name'] not in self.link.names:
            raise ValueError('Choose a connected MCP tool from integration_status')
        task = self.app.live.task if self.app.live and self.app.live.task else self.app.runtime.task_id
        if not task:
            raise ValueError('MCP execution requires an active user task')
        return await self.app.tools.call(task, args['name'], json.loads(args['arguments']), set())

    def register(self):
        tools = self.app.tools
        tools.add(Tool('plugin_catalog', 'List reviewed KAIRO plugin packages', parameters(), lambda a:a, lambda a:self.plugins.catalog()))
        tools.add(Tool('plugin_prepare', 'Prepare public-document adapters from a reviewed plugin; testing/activation still required', parameters(plugin=80), lambda a:a, self.plugins.prepare))
        tools.add(Tool('integration_status', 'List connected MCP tools and connection status', parameters(), lambda a:a, lambda a:self.status()))
        tools.add(Tool('integration_discover', 'Inspect a local MCP server manifest without executing tools', parameters(url=2000,transport=30), lambda a:a, self.discover))
        tools.add(Tool('integration_connect', 'Connect explicitly selected loopback MCP tools after owner review', parameters(url=2000,transport=30,tools=2000), self.prepare_connection, self.connect, True))
        tools.add(Tool('integration_local', 'Start bundled read-only local MCP utilities: time/system information/text helpers', parameters(), lambda a:a, lambda a:self.start_local()))
        tools.add(Tool('integration_call', 'Call a connected MCP tool with JSON arguments. Preserves its approval gate, including in Live sessions.', parameters(name=49,arguments=32000), lambda a:a, self.call))
