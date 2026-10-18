import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kairo.workspace import Workspace

workspace = Workspace({'AURORA': {'root': 'D:/AURORA/AuroraUE5', 'commands': {}}}, Path(sys.argv[1]).parent)
report = {'project': 'AURORA', 'root': str(workspace.root('AURORA')), 'files': []}
for relative in ['README.md', 'AuroraDayForever.uproject', 'Reference/AURORA_STORY_BIBLE.md', 'Reference/AURORA_CHARACTER_BIBLE.md', 'Reference/AURORA_VISUAL_BIBLE.md']:
    result = workspace.read('AURORA', relative)
    report['files'].append({'path': relative, 'sha256': result['sha256'], 'characters': len(result['text'])})
report.update({'writes': 0, 'engine_build': 'not run', 'reason': 'Initial approved scope is read-only inspection; command aliases must be configured explicitly.'})
Path(sys.argv[1]).write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
