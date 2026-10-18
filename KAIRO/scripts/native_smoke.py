from pathlib import Path
import tempfile
from kairo.application import Application
from kairo.native import NativeHost

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='kairo-smoke-') as state:
        NativeHost(Application(state), Path(__file__).resolve().parents[1]/'ui/out').run(smoke=True)
