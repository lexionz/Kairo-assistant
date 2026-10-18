import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from kairo.application import Application


def main():
    parser = argparse.ArgumentParser(prog="kairo")
    parser.add_argument("command", choices=["native", "web", "desktop", "doctor", "speech-probe"], nargs="?", default="native")
    parser.add_argument("--port", type=int, default=0)
    candidates = [Path(__file__).resolve().parents[2] / "ui/out", Path(sys.executable).resolve().parents[2] / "ui/out"]
    parser.add_argument("--ui", default=str(next((p for p in candidates if (p / "index.html").is_file()), candidates[0])))
    parser.add_argument("--data-dir")
    args = parser.parse_args()
    if args.command == "doctor":
        print(json.dumps({"python": __import__('sys').version, "windows": os.name == "nt", "cloud_key_present": bool(os.environ.get("KAIRO_API_KEY")), "aurora_exists": Path("D:/AURORA/AuroraUE5").is_dir(), "note": "This check does not record audio or prove a live model connection."}, indent=2))
        return
    application = Application(args.data_dir)
    if args.command == "native":
        try:
            from kairo.native import NativeHost
            NativeHost(application, args.ui).run()
        except Exception:
            if os.name == 'nt':
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, 'KAIRO could not start. Run Setup-KAIRO.cmd and ensure Microsoft Edge WebView2 Runtime is installed. For diagnostics run .venv\\Scripts\\python.exe -m kairo native in this folder.', 'KAIRO startup error', 0x10)
            raise
        return
    if args.command == "web":
        from kairo.web import serve
        asyncio.run(serve(application, args.ui, args.port))
        return
    if args.command == "speech-probe":
        executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        probe = application.directory / "speech-probe.wav"
        result = subprocess.run([str(executable), "-NoProfile", "-File", str(Path(__file__).with_name("speech.ps1")), "-Operation", "probe", "-AudioPath", str(probe)], capture_output=True, text=True, timeout=30, creationflags=0x08000000)
        print(result.stdout or result.stderr)
        raise SystemExit(result.returncode)
    from kairo.desktop import Desktop
    Desktop(application).run()
