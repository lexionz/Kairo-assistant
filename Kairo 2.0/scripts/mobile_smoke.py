from pathlib import Path
import json
import time
import webview

window=webview.create_window('KAIRO mobile layout check',html=(Path(__file__).resolve().parents[1]/'src/kairo/companion.html').read_text(encoding='utf-8'),width=390,height=844,min_size=(320,400))
def check():
    window.events.loaded.wait(20)
    window.evaluate_js("window.fetch=async()=>({ok:true,json:async()=>({token:'fixture',scopes:['screen','pointer','keyboard','media','windows']})});document.getElementById('pair').click()")
    time.sleep(1)
    result=window.evaluate_js("({width:innerWidth,contentWidth:document.documentElement.scrollWidth,sections:Array.from(document.querySelectorAll('[data-scope]')).filter(s=>!s.hidden).map(s=>s.dataset.scope),buttons:Array.from(document.querySelectorAll('button')).map(b=>b.textContent)})")
    print(json.dumps(result),flush=True)
    window.destroy()
webview.start(check,gui='edgechromium')
