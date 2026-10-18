"""Explicit, backup-first installation into the previously inspected KAIRO installation."""
from datetime import datetime
from pathlib import Path
import shutil
import subprocess


def main():
    source = Path(__file__).resolve().parents[1]
    destination = Path('D:/KAIRO/app').resolve()
    if source == destination:
        raise SystemExit('Already in the installed folder; run Setup-KAIRO.cmd here.')
    if not (destination / 'src/kairo/application.py').is_file():
        raise SystemExit('Expected existing KAIRO installation at D:/KAIRO/app; nothing changed.')
    if destination.parent != Path('D:/KAIRO').resolve():
        raise SystemExit('Unexpected destination; nothing changed.')
    backup = destination.parent / ('backup-before-native-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    ignore = shutil.ignore_patterns('.venv', 'node_modules', '.next', '__pycache__', '.pytest_cache', 'build', '*.egg-info', '*.pyc')
    shutil.copytree(destination, backup, ignore=ignore)
    print('Application backup:', backup)
    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore)
    python = destination / '.venv/Scripts/python.exe'
    if not python.is_file():
        raise SystemExit('Files copied. Run Setup-KAIRO.cmd in D:/KAIRO/app to create its environment.')
    result = subprocess.run([str(python), '-m', 'pip', 'install', str(destination) + '[native,companion]'], cwd=destination)
    if result.returncode:
        raise SystemExit('Dependency installation failed. Run Setup-KAIRO.cmd before starting. The application backup remains at ' + str(backup))
    print('Installed. Double-click D:/KAIRO/app/Start-KAIRO.cmd. User configuration and AURORA were not copied or changed.')


if __name__ == '__main__':
    main()
