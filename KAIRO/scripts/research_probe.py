import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kairo.research import Research

async def main():
    research = Research(max_sources=3)
    source = await research.retrieve('https://docs.python.org/3/library/asyncio-task.html')
    report = {'document': {k: source[k] for k in ('id', 'title', 'url', 'retrieved_at', 'sha256', 'modified')}, 'text_characters': len(source['text'])}
    try:
        papers = await research.papers('retrieval augmented generation')
        report['papers'] = papers
    except Exception as exc:
        report['papers_error'] = str(exc)
    try:
        result = await research.search('Python asyncio documentation')
        report['search'] = {'urls': result['urls'], 'source_id': result['source_id']}
    except Exception as exc:
        report['search_error'] = str(exc)
    print(json.dumps(report, indent=2))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=2), encoding='utf-8')

asyncio.run(main())
