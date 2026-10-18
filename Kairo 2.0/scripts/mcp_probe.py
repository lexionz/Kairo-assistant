import asyncio
import json
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

if len(sys.argv) > 1 and sys.argv[1] == '--server':
    from mcp.server.fastmcp import FastMCP
    server = FastMCP('KAIRO protocol test', host='127.0.0.1', port=int(sys.argv[2]))
    @server.tool()
    def word_count(text: str) -> int:
        return len(text.split())
    @server.tool()
    def unapproved() -> str:
        return 'must not be exposed'
    server.run(transport='sse')
else:
    from kairo.authority import Authority
    from kairo.contracts import Events
    from kairo.journal import Journal
    from kairo.mcp_link import MCPLink
    from kairo.tools import Tools
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([sys.executable, __file__, '--server', str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
    async def run():
        for _ in range(50):
            try:
                reader, writer = await asyncio.open_connection('127.0.0.1', port)
                writer.close()
                await writer.wait_closed()
                break
            except OSError:
                await asyncio.sleep(.1)
        with tempfile.TemporaryDirectory(prefix='kairo-mcp-') as directory:
            events = Events()
            gate = Authority(events)
            journal = Journal(directory)
            tools = Tools(gate, journal, events)
            events.subscribe(lambda event: gate.decide(event.payload['token'], event.payload['task'], True) if event.kind == 'approval' else None)
            link = MCPLink()
            try:
                names = await link.connect({'url': f'http://127.0.0.1:{port}/sse', 'allow': ['word_count']}, tools)
                assert names == ['mcp_word_count']
                result = await tools.call('test', 'mcp_word_count', {'text': 'KAIRO tests real protocols'}, set())
                assert result['content'][0]['text'] == '4'
                report = {'connected': names, 'result': result, 'unapproved_registered': 'mcp_unapproved' in tools.items}
                print(json.dumps(report))
                if len(sys.argv) > 1:
                    Path(sys.argv[1]).write_text(json.dumps(report, indent=2))
            finally:
                await link.close()
                journal.close()
    try:
        asyncio.run(run())
    finally:
        process.terminate()
        process.wait(timeout=5)
