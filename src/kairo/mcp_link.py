from contextlib import AsyncExitStack
from urllib.parse import urlsplit
from kairo.contracts import Tool


class MCPLink:
    def __init__(self):
        self.stack = None
        self.names = []
        self.tools = None

    async def connect(self, config, tools):
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        if self.stack:
            raise ValueError("MCP is already connected")
        parsed = urlsplit(config["url"])
        if parsed.hostname not in {"127.0.0.1", "::1"} or parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            raise ValueError("MCP must use an explicit loopback endpoint")
        allowed = config.get("allow", [])
        if not allowed:
            raise ValueError("MCP tool allowlist is empty")
        stack = AsyncExitStack()
        self.tools = tools
        try:
            reader, writer = await stack.enter_async_context(sse_client(config["url"]))
            session = await stack.enter_async_context(ClientSession(reader, writer))
            await session.initialize()
            manifests = await session.list_tools()
            names = []
            for manifest in manifests.tools:
                schema = manifest.inputSchema
                if manifest.name not in allowed or schema.get("type") != "object" or any(v.get("type") not in {"string", "integer", "boolean"} for v in schema.get("properties", {}).values()):
                    continue
                remote_name = manifest.name

                async def execute(prepared, remote=remote_name):
                    async with __import__('asyncio').timeout(30):
                        response = await session.call_tool(remote, prepared["arguments"])
                    return {"error": "MCP reported failure", "content": [c.model_dump() for c in response.content]} if response.isError else {"content": [c.model_dump() for c in response.content]}

                def prepare(args, remote=remote_name):
                    return {"server": config["url"], "tool": remote, "arguments": args}

                name = "mcp_" + remote_name
                tools.add(Tool(name, "Allowlisted external MCP tool " + remote_name, schema, prepare, execute, True))
                names.append(name)
                self.names.append(name)
            self.stack = stack
            return names
        except BaseException:
            await stack.aclose()
            for name in self.names:
                tools.items.pop(name, None)
            self.names.clear()
            raise

    async def close(self):
        if self.stack:
            await self.stack.aclose()
            self.stack = None
        if self.tools:
            for name in self.names:
                self.tools.items.pop(name, None)
        self.names.clear()
