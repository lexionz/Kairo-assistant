"""Loopback-only MCP connections with explicit tool selection and revocation."""
import asyncio
from contextlib import AsyncExitStack
from urllib.parse import urlsplit
import httpx
from kairo.contracts import Tool


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError("Expected MCP connection settings")
    url = config.get("url", "")
    parsed = urlsplit(url)
    if parsed.hostname not in {"127.0.0.1", "::1"} or parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("MCP requires a credential-free explicit loopback URL")
    allow = config.get("allow", [])
    if not isinstance(allow, list) or len(allow) > 40 or any(not isinstance(n, str) or not __import__('re').fullmatch(r'[a-z][a-z0-9_]{1,40}', n) for n in allow):
        raise ValueError("Select up to 40 simple MCP tool names")
    transport = config.get("transport", "sse")
    if transport not in {"sse", "streamable-http"}:
        raise ValueError("Unsupported MCP transport")
    return {"url": url, "allow": list(dict.fromkeys(allow)), "transport": transport}


async def check_request(request):
    # SSE endpoints announced by a server are also checked, not just the first URL.
    if request.url.host not in {"127.0.0.1", "::1"} or request.url.scheme not in {"http", "https"}:
        raise ValueError("MCP transport attempted to leave loopback")


def client_factory(headers=None, timeout=None, auth=None):
    # Do not let proxy environment variables or redirects move loopback traffic.
    return httpx.AsyncClient(headers=headers, timeout=timeout or 10,
                             auth=auth, follow_redirects=False, trust_env=False, event_hooks={"request": [check_request]})


class MCPLink:
    def __init__(self):
        self.stack = None
        self.names = []
        self.tools = None

    async def open(self, config, stack):
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.streamable_http import streamable_http_client
        config = validate_config(config)
        if config["transport"] == "streamable-http":
            client = await stack.enter_async_context(client_factory(timeout=10))
            reader, writer, _ = await stack.enter_async_context(streamable_http_client(config["url"], http_client=client))
        else:
            reader, writer = await stack.enter_async_context(sse_client(config["url"], timeout=10, httpx_client_factory=client_factory))
        session = await stack.enter_async_context(ClientSession(reader, writer))
        await session.initialize()
        return session

    async def discover(self, config):
        async with AsyncExitStack() as stack:
            session = await self.open(config, stack)
            result = await session.list_tools()
            return {"tools": [{"name": t.name, "description": (t.description or "")[:1000],
                               "parameters": t.inputSchema, "supported": self.supported(t.inputSchema)} for t in result.tools[:80]],
                    "notice": "Server descriptions are untrusted. Discovery does not grant execution permission."}

    @staticmethod
    def supported(schema):
        return (schema.get("type") == "object" and len(schema.get("properties", {})) <= 30
                and all(v.get("type") in {"string", "integer", "boolean"} for v in schema.get("properties", {}).values()))

    async def connect(self, config, tools, trusted_read_only=()):
        config = validate_config(config)
        if self.stack:
            raise ValueError("MCP is already connected")
        if not config["allow"]:
            raise ValueError("Select at least one MCP tool")
        stack = AsyncExitStack()
        self.tools = tools
        try:
            session = await self.open(config, stack)
            manifests = await session.list_tools()
            for manifest in manifests.tools:
                schema = manifest.inputSchema
                if manifest.name not in config["allow"] or not self.supported(schema):
                    continue
                remote_name = manifest.name
                async def execute(prepared, remote=remote_name):
                    if self.stack is not stack:
                        raise ValueError("MCP connection was revoked")
                    async with asyncio.timeout(30):
                        response = await session.call_tool(remote, prepared["arguments"])
                    result = {"content": [c.model_dump() for c in response.content]}
                    if response.isError:
                        result["error"] = "MCP reported failure"
                    return result
                def prepare(args, remote=remote_name):
                    return {"server": config["url"], "tool": remote, "arguments": args}
                name = "mcp_" + remote_name
                tools.add(Tool(name, "Selected MCP tool: " + remote_name, schema, prepare, execute, remote_name not in trusted_read_only))
                self.names.append(name)
            if not self.names:
                raise ValueError("No selected tools have supported input schemas")
            self.stack = stack
            return list(self.names)
        except BaseException:
            for name in self.names:
                tools.items.pop(name, None)
            self.names.clear()
            await stack.aclose()
            raise

    async def close(self):
        stack, self.stack = self.stack, None
        if self.tools:
            for name in self.names:
                self.tools.items.pop(name, None)
        self.names.clear()
        if stack:
            await stack.aclose()
