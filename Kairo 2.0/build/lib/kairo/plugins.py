"""Small declarative plugin library. Packages can only propose public-read adapters."""
PACKAGES = {
    'python_docs': {'name': 'Python reference', 'description': 'Official Python documentation for engineering tasks.',
                    'adapters': [{'name': 'adapter_python_asyncio', 'url': 'https://docs.python.org/3/library/asyncio.html', 'description': 'Official Python asyncio reference'},
                                 {'name': 'adapter_python_library', 'url': 'https://docs.python.org/3/library/index.html', 'description': 'Official Python standard library reference'}]},
    'mcp_docs': {'name': 'MCP reference', 'description': 'Official Model Context Protocol integration documentation.',
                 'adapters': [{'name': 'adapter_mcp_introduction', 'url': 'https://modelcontextprotocol.io/introduction', 'description': 'Official MCP integration introduction'}]},
    'local_utilities': {'name': 'Local utilities', 'description': 'Bundled read-only MCP tools: time, system info, word counts, JSON formatting.', 'adapters': []},
}


class PluginLibrary:
    def __init__(self, capabilities):
        self.capabilities = capabilities

    def catalog(self):
        return {'plugins': [{'id': identity, **package} for identity, package in PACKAGES.items()],
                'notice': 'Plugins contain reviewed declarative definitions, never downloaded executable code.'}

    def prepare(self, args):
        package = PACKAGES[args['plugin']]
        results = []
        for adapter in package['adapters']:
            if adapter['name'] in self.capabilities.tools.items:
                results.append({'name': adapter['name'], 'status': 'active'})
            else:
                results.append(self.capabilities.propose(adapter))
        return {'plugin': args['plugin'], 'adapters': results,
                'next': 'Test and activate proposed adapters. For local_utilities use integration_local to start the bundled server.'}
