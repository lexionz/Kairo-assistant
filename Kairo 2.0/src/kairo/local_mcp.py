"""Bundled local read-only MCP utilities. No filesystem or process-execution tools."""
from datetime import datetime
import json
import os
import platform
import re
from mcp.server.fastmcp import FastMCP

READ_ONLY_TOOLS = ('get_current_time', 'get_system_info', 'word_count', 'format_json')


def create_server(port=8769):
    server = FastMCP('KAIRO local utilities', host='127.0.0.1', port=port,
                     stateless_http=True, json_response=True, log_level='WARNING')

    @server.tool()
    def get_current_time() -> dict:
        """Read the current local time and UTC offset."""
        return {'time': datetime.now().astimezone().isoformat()}

    @server.tool()
    def get_system_info() -> dict:
        """Read OS, architecture and CPU count without usernames or environment secrets."""
        return {'os': platform.system(), 'release': platform.release(), 'architecture': platform.machine(),
                'logical_cpus': os.cpu_count(), 'python': platform.python_version()}

    @server.tool()
    def word_count(text: str) -> dict:
        """Count characters, whitespace-delimited words and lines in supplied text."""
        if len(text) > 32000:
            raise ValueError('Text exceeds 32,000 characters')
        return {'characters': len(text), 'words': len(re.findall(r'\S+', text)), 'lines': len(text.splitlines())}

    @server.tool()
    def format_json(text: str) -> dict:
        """Validate and pretty-print supplied JSON; no file access."""
        if len(text) > 32000:
            raise ValueError('JSON exceeds 32,000 characters')
        return {'formatted': json.dumps(json.loads(text), indent=2, ensure_ascii=False)}
    return server


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8769)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Choose a non-privileged port')
    create_server(args.port).run(transport='streamable-http')


if __name__ == '__main__': main()
