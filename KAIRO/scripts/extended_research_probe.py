import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kairo.research import Research

async def run():
    research = Research(max_sources=2)
    report = {}
    sources = {
        'pdf': 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',
        'repository': 'https://raw.githubusercontent.com/SAGAR-TAMANG/friday-tony-stark-demo/4d85750ae4c60c88850a6c69107e91bf02300673/friday/tools/system.py'
    }
    for kind, url in sources.items():
        try:
            source = await research.retrieve(url, 'paper_text' if kind == 'pdf' else 'repository_code')
            report[kind] = {key: source[key] for key in ('id', 'url', 'retrieved_at', 'sha256', 'kind')}
            report[kind]['characters'] = len(source['text'])
            report[kind]['contains_expected_text'] = 'Dummy PDF file' in source['text'] if kind == 'pdf' else 'def get_current_time' in source['text']
        except Exception as exc:
            report[kind] = {'error': str(exc)}
    print(json.dumps(report, indent=2))
    Path(sys.argv[1]).write_text(json.dumps(report, indent=2))

asyncio.run(run())
