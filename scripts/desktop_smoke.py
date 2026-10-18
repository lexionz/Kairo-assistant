import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kairo.application import Application
from kairo.desktop import Desktop

output = Path(sys.argv[1]).resolve()
output.mkdir(parents=True, exist_ok=True)
app = Application(output / 'smoke-state')
ui = Desktop(app, smoke=True)
states = list(ui.colors)
results = []

def check(index=0):
    if index == len(states):
        ui.show_panel()
        results.append({'panel': bool(ui.panel.winfo_exists()), 'microphone_opened': app.voice.process is not None})
        (output / 'desktop.json').write_text(json.dumps(results, indent=2))
        ui.root.after(500, ui.close)
        return
    state = states[index]
    ui.state = state
    ui.text = 'Visual test · ' + state
    ui.draw()
    ui.root.update_idletasks()
    results.append({'state': state, 'canvas_items': len(ui.canvas.find_all()), 'size': [ui.root.winfo_width(), ui.root.winfo_height()]})
    ui.root.after(120, lambda: check(index + 1))

ui.root.after(300, check)
ui.run()
assert not any(row.get('microphone_opened', False) for row in results)
print(json.dumps(results))
